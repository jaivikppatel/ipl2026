"""
Fantasy Cricket API Routes
All /api/fantasy/* endpoints.
"""

import json
from datetime import datetime, timezone
from typing import Optional

import mysql.connector
from fastapi import APIRouter, HTTPException, Depends, Header, Query, status
from pydantic import BaseModel

fantasy_router = APIRouter(prefix='/api/fantasy', tags=['fantasy'])


# ============================================================================
# LOCAL HELPERS (import get_current_user and verify_admin from app context)
# ============================================================================

def _get_db():
    """Import at call time to avoid circular imports."""
    from app import get_db_connection
    return get_db_connection()


def _current_user_dep():
    from app import get_current_user
    return get_current_user


def _admin_dep():
    from app import verify_admin
    return verify_admin


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TeamSubmitPlayer(BaseModel):
    player_id: int
    is_captain: bool = False
    is_vice_captain: bool = False


class TeamSubmitRequest(BaseModel):
    players: list[TeamSubmitPlayer]  # Exactly 11


class PlayerCreditUpdate(BaseModel):
    credits: Optional[float] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class SeriesCreate(BaseModel):
    name: str
    cricapi_series_id: str


class SeriesUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

TEAM_SIZE = 11
MAX_CREDITS = 100.0
MAX_FROM_ONE_TEAM = 7
ROLE_MINS = {'WK': 1, 'BAT': 1, 'AR': 1, 'BOWL': 1}


def _validate_team(players_with_info: list) -> Optional[str]:
    """
    Validate team composition.
    players_with_info: list of dicts with keys: player_id, is_captain, is_vice_captain, credits, role, team_id
    Returns error string or None if valid.
    """
    if len(players_with_info) != TEAM_SIZE:
        return f'Team must have exactly {TEAM_SIZE} players, got {len(players_with_info)}'

    total_credits = sum(float(p['credits']) for p in players_with_info)
    if total_credits > MAX_CREDITS:
        return f'Total credits {total_credits:.1f} exceeds limit of {MAX_CREDITS}'

    team_counts: dict[int, int] = {}
    role_counts: dict[str, int] = {}
    captains = 0
    vcs = 0

    for p in players_with_info:
        tid = p['team_id']
        team_counts[tid] = team_counts.get(tid, 0) + 1
        role = p['role']
        # WK counts as BAT for minimum check
        role_counts[role] = role_counts.get(role, 0) + 1
        if role == 'WK':
            role_counts['BAT'] = role_counts.get('BAT', 0) + 1
        if p.get('is_captain'):
            captains += 1
        if p.get('is_vice_captain'):
            vcs += 1

    for tid, cnt in team_counts.items():
        if cnt > MAX_FROM_ONE_TEAM:
            return f'Max {MAX_FROM_ONE_TEAM} players from one team allowed'

    for role, min_count in ROLE_MINS.items():
        if role_counts.get(role, 0) < min_count:
            role_label = {'WK': 'Wicket-Keeper', 'BAT': 'Batsman', 'AR': 'All-Rounder', 'BOWL': 'Bowler'}.get(role, role)
            return f'Need at least {min_count} {role_label}(s)'

    if captains != 1:
        return 'Exactly 1 Captain must be selected'
    if vcs != 1:
        return 'Exactly 1 Vice-Captain must be selected'

    # Captain and VC must be different players
    cap_ids = [p['player_id'] for p in players_with_info if p.get('is_captain')]
    vc_ids = [p['player_id'] for p in players_with_info if p.get('is_vice_captain')]
    if cap_ids and vc_ids and cap_ids[0] == vc_ids[0]:
        return 'Captain and Vice-Captain must be different players'

    return None


# ============================================================================
# SERIES ENDPOINT
# ============================================================================

@fantasy_router.get('/series')
async def get_series(
    authorization: Optional[str] = Header(None)
):
    """List all active series. If authenticated, includes user_has_access per series."""
    current_user_id = None
    if authorization:
        try:
            from app import get_current_user
            user = await get_current_user(authorization)
            current_user_id = user['user_id']
        except Exception:
            pass

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            'SELECT id, name, cricapi_series_id, is_active FROM fantasy_series WHERE is_active = 1 ORDER BY id ASC'
        )
        rows = cursor.fetchall()

        # Build access map for authenticated user
        access_set = set()
        if current_user_id:
            cursor.execute(
                'SELECT series_id FROM fantasy_series_access WHERE user_id = %s',
                (current_user_id,)
            )
            access_set = {r['series_id'] for r in cursor.fetchall()}

        series = [
            {
                'id': row['id'],
                'name': row['name'],
                'cricapi_series_id': row['cricapi_series_id'],
                'is_active': bool(row['is_active']),
                'user_has_access': row['id'] in access_set,
            }
            for row in rows
        ]
        return {'series': series}
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# USER ENDPOINTS
# ============================================================================

@fantasy_router.get('/matches')
async def get_matches(
    series_id: Optional[int] = Query(None, description='Filter matches by series ID'),
):
    """List matches with status, optionally scoped to a series."""
    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        if series_id is not None:
            cursor.execute(
                '''SELECT
                     fms.id, fms.cricapi_match_id, fms.match_name, fms.short_name,
                     fms.match_date, fms.match_datetime_gmt, fms.venue,
                     fms.status, fms.status_note, fms.live_score, fms.squad_fetched, fms.playing_xi_announced,
                     t1.short_name AS team1_short, t1.full_name AS team1_name, t1.primary_color AS team1_color,
                     t2.short_name AS team2_short, t2.full_name AS team2_name, t2.primary_color AS team2_color
                   FROM fantasy_match_schedule fms
                   LEFT JOIN fantasy_ipl_teams t1 ON fms.team1_id = t1.id
                   LEFT JOIN fantasy_ipl_teams t2 ON fms.team2_id = t2.id
                   WHERE fms.series_id = %s
                   ORDER BY fms.match_datetime_gmt ASC, fms.match_date ASC''',
                (series_id,)
            )
        else:
            cursor.execute(
                '''SELECT
                     fms.id, fms.cricapi_match_id, fms.match_name, fms.short_name,
                     fms.match_date, fms.match_datetime_gmt, fms.venue,
                     fms.status, fms.status_note, fms.live_score, fms.squad_fetched, fms.playing_xi_announced,
                     t1.short_name AS team1_short, t1.full_name AS team1_name, t1.primary_color AS team1_color,
                     t2.short_name AS team2_short, t2.full_name AS team2_name, t2.primary_color AS team2_color
                   FROM fantasy_match_schedule fms
                   LEFT JOIN fantasy_ipl_teams t1 ON fms.team1_id = t1.id
                   LEFT JOIN fantasy_ipl_teams t2 ON fms.team2_id = t2.id
                   ORDER BY fms.match_datetime_gmt ASC, fms.match_date ASC'''
            )
        matches = []
        for row in cursor.fetchall():
            matches.append({
                'id': row['id'],
                'cricapi_match_id': row['cricapi_match_id'],
                'match_name': row['match_name'],
                'short_name': row['short_name'],
                'match_date': row['match_date'].isoformat() if row['match_date'] else None,
                'match_datetime_gmt': row['match_datetime_gmt'].isoformat() if row['match_datetime_gmt'] else None,
                'venue': row['venue'],
                'status': row['status'],
                'status_note': row['status_note'],
                'live_score': json.loads(row['live_score']) if row.get('live_score') else [],
                'squad_fetched': bool(row['squad_fetched']),
                'playing_xi_announced': bool(row['playing_xi_announced']),
                'team1': {'short': row['team1_short'], 'name': row['team1_name'], 'color': row['team1_color']},
                'team2': {'short': row['team2_short'], 'name': row['team2_name'], 'color': row['team2_color']},
            })
        return {'matches': matches}
    finally:
        cursor.close()
        conn.close()


@fantasy_router.get('/matches/{match_id}/players')
async def get_match_players(
    match_id: int,
    authorization: Optional[str] = Header(None)
):
    """
    Get players available for team selection for a given match.
    If squad has been fetched, returns only the announced squad.
    Otherwise returns all active players from both playing teams.
    """
    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get match info
        cursor.execute(
            'SELECT team1_id, team2_id, squad_fetched, playing_xi_announced FROM fantasy_match_schedule WHERE id = %s',
            (match_id,)
        )
        match = cursor.fetchone()
        if not match:
            raise HTTPException(status_code=404, detail='Match not found')

        if match['squad_fetched']:
            # Return announced squad
            cursor.execute(
                '''SELECT
                     p.id, p.name, p.role, p.credits, p.batting_style, p.bowling_style, p.country, p.image_url,
                     t.short_name AS team_short, t.full_name AS team_name, t.primary_color,
                     fqs.is_playing_xi
                   FROM fantasy_match_squads fqs
                   JOIN fantasy_ipl_players p ON fqs.player_id = p.id
                   JOIN fantasy_ipl_teams t ON p.team_id = t.id
                   WHERE fqs.match_id = %s AND fqs.is_announced = 1 AND p.is_active = 1
                   ORDER BY t.short_name, p.role, p.name''',
                (match_id,)
            )
        else:
            # Return all active players from both teams
            team_ids = [match['team1_id'], match['team2_id']]
            team_ids = [tid for tid in team_ids if tid]
            if not team_ids:
                return {'players': [], 'squad_announced': False, 'playing_xi_announced': False}

            placeholders = ','.join(['%s'] * len(team_ids))
            cursor.execute(
                f'''SELECT
                     p.id, p.name, p.role, p.credits, p.batting_style, p.bowling_style, p.country, p.image_url,
                     t.short_name AS team_short, t.full_name AS team_name, t.primary_color,
                     0 AS is_playing_xi
                   FROM fantasy_ipl_players p
                   JOIN fantasy_ipl_teams t ON p.team_id = t.id
                   WHERE p.team_id IN ({placeholders}) AND p.is_active = 1
                   ORDER BY t.short_name, p.role, p.name''',
                team_ids
            )

        rows = cursor.fetchall()
        players = [
            {
                'id': r['id'],
                'name': r['name'],
                'role': r['role'],
                'credits': float(r['credits']),
                'batting_style': r['batting_style'],
                'bowling_style': r['bowling_style'],
                'country': r['country'],
                'image_url': r['image_url'],
                'team_short': r['team_short'],
                'team_name': r['team_name'],
                'team_color': r['primary_color'],
                'is_playing_xi': bool(r.get('is_playing_xi', False)),
            }
            for r in rows
        ]
        return {
            'players': players,
            'squad_announced': bool(match['squad_fetched']),
            'playing_xi_announced': bool(match['playing_xi_announced']),
        }
    finally:
        cursor.close()
        conn.close()


@fantasy_router.get('/matches/{match_id}/my-team')
async def get_my_team(
    match_id: int,
    authorization: Optional[str] = Header(None)
):
    """Get the current user's fantasy team for a match."""
    from app import get_current_user
    current_user = await get_current_user(authorization)
    user_id = current_user['user_id']

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            '''SELECT id, is_locked, total_credits_used, created_at, updated_at
               FROM fantasy_user_selections
               WHERE user_id = %s AND match_id = %s''',
            (user_id, match_id)
        )
        selection = cursor.fetchone()
        if not selection:
            return {'team': None}

        cursor.execute(
            '''SELECT
                 futp.player_id, futp.is_captain, futp.is_vice_captain,
                 p.name, p.role, p.credits, p.image_url,
                 t.short_name AS team_short, t.primary_color
               FROM fantasy_user_team_players futp
               JOIN fantasy_ipl_players p ON futp.player_id = p.id
               JOIN fantasy_ipl_teams t ON p.team_id = t.id
               WHERE futp.selection_id = %s''',
            (selection['id'],)
        )
        players = cursor.fetchall()

        # Get points if available
        player_ids = [p['player_id'] for p in players]
        points_map = {}
        if player_ids:
            placeholders = ','.join(['%s'] * len(player_ids))
            cursor.execute(
                f'SELECT player_id, fantasy_points FROM fantasy_player_match_stats WHERE match_id = %s AND player_id IN ({placeholders})',
                [match_id] + player_ids
            )
            for row in cursor.fetchall():
                points_map[row['player_id']] = float(row['fantasy_points'])

        # Get leaderboard entry
        cursor.execute(
            'SELECT total_points, rank FROM fantasy_match_leaderboard WHERE match_id = %s AND user_id = %s',
            (match_id, user_id)
        )
        lb = cursor.fetchone()

        return {
            'team': {
                'selection_id': selection['id'],
                'is_locked': bool(selection['is_locked']),
                'total_credits_used': float(selection['total_credits_used']),
                'created_at': selection['created_at'].isoformat() if selection['created_at'] else None,
                'players': [
                    {
                        'player_id': p['player_id'],
                        'name': p['name'],
                        'role': p['role'],
                        'credits': float(p['credits']),
                        'image_url': p['image_url'],
                        'team_short': p['team_short'],
                        'team_color': p['primary_color'],
                        'is_captain': bool(p['is_captain']),
                        'is_vice_captain': bool(p['is_vice_captain']),
                        'base_points': points_map.get(p['player_id'], 0),
                        'total_points': (
                            points_map.get(p['player_id'], 0) * (2.0 if p['is_captain'] else 1.5 if p['is_vice_captain'] else 1.0)
                        ),
                    }
                    for p in players
                ],
                'leaderboard': {
                    'total_points': float(lb['total_points']) if lb else 0,
                    'rank': lb['rank'] if lb else None,
                } if lb else None
            }
        }
    finally:
        cursor.close()
        conn.close()


@fantasy_router.post('/matches/{match_id}/team')
async def submit_team(
    match_id: int,
    request: TeamSubmitRequest,
    authorization: Optional[str] = Header(None)
):
    """Create or update the user's fantasy team for a match."""
    from app import get_current_user
    current_user = await get_current_user(authorization)
    user_id = current_user['user_id']

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check match exists and is not locked/started
        cursor.execute(
            'SELECT id, series_id, match_datetime_gmt, status FROM fantasy_match_schedule WHERE id = %s',
            (match_id,)
        )
        match = cursor.fetchone()
        if not match:
            raise HTTPException(status_code=404, detail='Match not found')

        # Series access check — user must have a row in fantasy_series_access for this series
        cursor.execute(
            'SELECT 1 FROM fantasy_series_access WHERE user_id = %s AND series_id = %s',
            (user_id, match['series_id'])
        )
        if not cursor.fetchone():
            raise HTTPException(
                status_code=403,
                detail='You are not allowed to participate in this series'
            )

        # Deadline check: match_datetime_gmt is stored as naive UTC
        if match['match_datetime_gmt']:
            deadline = match['match_datetime_gmt'].replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= deadline:
                raise HTTPException(status_code=400, detail='Team cannot be changed after match has started')

        if match['status'] in ('completed', 'abandoned'):
            raise HTTPException(status_code=400, detail='Match has already ended')

        # Validate we have 11 unique players
        player_ids = [p.player_id for p in request.players]
        if len(set(player_ids)) != TEAM_SIZE:
            raise HTTPException(status_code=400, detail=f'Team must have exactly {TEAM_SIZE} unique players')

        # Fetch player details from DB
        placeholders = ','.join(['%s'] * len(player_ids))
        cursor.execute(
            f'SELECT id, credits, role, team_id, is_active FROM fantasy_ipl_players WHERE id IN ({placeholders})',
            player_ids
        )
        db_players = {r['id']: r for r in cursor.fetchall()}

        if len(db_players) != TEAM_SIZE:
            raise HTTPException(status_code=400, detail='One or more players not found')

        # Build enriched list for validation
        enriched = []
        for submitted in request.players:
            db_p = db_players[submitted.player_id]
            if not db_p['is_active']:
                raise HTTPException(status_code=400, detail=f'Player {submitted.player_id} is not active')
            enriched.append({
                'player_id': submitted.player_id,
                'is_captain': submitted.is_captain,
                'is_vice_captain': submitted.is_vice_captain,
                'credits': db_p['credits'],
                'role': db_p['role'],
                'team_id': db_p['team_id'],
            })

        error = _validate_team(enriched)
        if error:
            raise HTTPException(status_code=400, detail=error)

        total_credits = sum(float(p['credits']) for p in enriched)

        # Upsert the selection
        cursor.execute(
            '''INSERT INTO fantasy_user_selections (user_id, match_id, total_credits_used)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 total_credits_used = VALUES(total_credits_used),
                 updated_at = NOW()''',
            (user_id, match_id, total_credits)
        )
        conn.commit()

        # Get selection id
        cursor.execute(
            'SELECT id FROM fantasy_user_selections WHERE user_id = %s AND match_id = %s',
            (user_id, match_id)
        )
        selection_id = cursor.fetchone()['id']

        # Delete old players and re-insert
        cursor.execute('DELETE FROM fantasy_user_team_players WHERE selection_id = %s', (selection_id,))
        for p in enriched:
            cursor.execute(
                '''INSERT INTO fantasy_user_team_players (selection_id, player_id, is_captain, is_vice_captain)
                   VALUES (%s, %s, %s, %s)''',
                (selection_id, p['player_id'], p['is_captain'], p['is_vice_captain'])
            )
        conn.commit()

        return {'message': 'Team saved successfully', 'selection_id': selection_id}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')
    finally:
        cursor.close()
        conn.close()


@fantasy_router.get('/matches/{match_id}/leaderboard')
async def get_match_leaderboard(
    match_id: int,
    authorization: Optional[str] = Header(None)
):
    """Get per-match fantasy leaderboard."""
    user_id = None
    if authorization:
        try:
            from app import get_current_user
            current_user = await get_current_user(authorization)
            user_id = current_user['user_id']
        except Exception:
            pass

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            '''SELECT
                 fml.rank, fml.total_points, fml.user_id,
                 u.display_name, u.profile_picture,
                 cp.name AS captain_name,
                 vcp.name AS vc_name
               FROM fantasy_match_leaderboard fml
               JOIN users u ON fml.user_id = u.id
               LEFT JOIN fantasy_ipl_players cp ON fml.captain_player_id = cp.id
               LEFT JOIN fantasy_ipl_players vcp ON fml.vice_captain_player_id = vcp.id
               WHERE fml.match_id = %s
               ORDER BY fml.rank ASC, fml.total_points DESC''',
            (match_id,)
        )
        rows = cursor.fetchall()
        entries = [
            {
                'rank': r['rank'],
                'user_id': r['user_id'],
                'display_name': r['display_name'],
                'profile_picture': r['profile_picture'],
                'total_points': float(r['total_points']),
                'captain_name': r['captain_name'],
                'vc_name': r['vc_name'],
                'is_current_user': (r['user_id'] == user_id),
            }
            for r in rows
        ]
        # Get match info
        cursor.execute(
            '''SELECT match_name, status, match_date FROM fantasy_match_schedule WHERE id = %s''',
            (match_id,)
        )
        match = cursor.fetchone()
        return {
            'match': {
                'id': match_id,
                'name': match['match_name'] if match else '',
                'status': match['status'] if match else '',
                'date': match['match_date'].isoformat() if match and match['match_date'] else None,
            },
            'leaderboard': entries,
        }
    finally:
        cursor.close()
        conn.close()


@fantasy_router.get('/matches/{match_id}/teams/{target_user_id}')
async def get_user_team(
    match_id: int,
    target_user_id: int,
    authorization: Optional[str] = Header(None)
):
    """Get another user's fantasy team for a match. Only revealed once match is live or completed."""
    from app import get_current_user
    await get_current_user(authorization)  # must be authenticated

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Only reveal teams after match has started
        cursor.execute(
            'SELECT status FROM fantasy_match_schedule WHERE id = %s',
            (match_id,)
        )
        match = cursor.fetchone()
        if not match:
            raise HTTPException(status_code=404, detail='Match not found')
        if match['status'] == 'upcoming':
            raise HTTPException(status_code=403, detail='Teams are hidden until the match starts')

        cursor.execute(
            'SELECT id FROM fantasy_user_selections WHERE user_id = %s AND match_id = %s',
            (target_user_id, match_id)
        )
        selection = cursor.fetchone()
        if not selection:
            raise HTTPException(status_code=404, detail='Team not found')

        cursor.execute(
            '''SELECT
                 futp.player_id, futp.is_captain, futp.is_vice_captain,
                 p.name, p.role, p.credits, p.image_url,
                 t.short_name AS team_short, t.primary_color
               FROM fantasy_user_team_players futp
               JOIN fantasy_ipl_players p ON futp.player_id = p.id
               JOIN fantasy_ipl_teams t ON p.team_id = t.id
               WHERE futp.selection_id = %s''',
            (selection['id'],)
        )
        players = cursor.fetchall()

        player_ids = [p['player_id'] for p in players]
        stats_map = {}  # player_id -> full stats row
        if player_ids:
            placeholders = ','.join(['%s'] * len(player_ids))
            cursor.execute(
                f'''SELECT player_id, fantasy_points,
                           runs_scored, balls_faced, fours, sixes, is_dismissed, is_duck,
                           wickets, balls_bowled, runs_conceded, maidens,
                           catches, stumpings, run_outs_direct, run_outs_indirect
                    FROM fantasy_player_match_stats
                    WHERE match_id = %s AND player_id IN ({placeholders})''',
                [match_id] + player_ids
            )
            for row in cursor.fetchall():
                stats_map[row['player_id']] = row

        cursor.execute(
            'SELECT display_name FROM users WHERE id = %s',
            (target_user_id,)
        )
        u = cursor.fetchone()

        return {
            'display_name': u['display_name'] if u else '',
            'players': [
                {
                    'player_id': p['player_id'],
                    'name': p['name'],
                    'role': p['role'],
                    'credits': float(p['credits']),
                    'image_url': p['image_url'],
                    'team_short': p['team_short'],
                    'team_color': p['primary_color'],
                    'is_captain': bool(p['is_captain']),
                    'is_vice_captain': bool(p['is_vice_captain']),
                    'base_points': float(stats_map[p['player_id']]['fantasy_points']) if p['player_id'] in stats_map else 0,
                    'total_points': round(
                        (float(stats_map[p['player_id']]['fantasy_points']) if p['player_id'] in stats_map else 0)
                        * (2.0 if p['is_captain'] else 1.5 if p['is_vice_captain'] else 1.0),
                        2
                    ),
                    'multiplier': 2.0 if p['is_captain'] else 1.5 if p['is_vice_captain'] else 1.0,
                    'stats': {
                        'runs': int(stats_map[p['player_id']]['runs_scored']) if p['player_id'] in stats_map else 0,
                        'balls': int(stats_map[p['player_id']]['balls_faced']) if p['player_id'] in stats_map else 0,
                        'fours': int(stats_map[p['player_id']]['fours']) if p['player_id'] in stats_map else 0,
                        'sixes': int(stats_map[p['player_id']]['sixes']) if p['player_id'] in stats_map else 0,
                        'wickets': int(stats_map[p['player_id']]['wickets']) if p['player_id'] in stats_map else 0,
                        'catches': int(stats_map[p['player_id']]['catches']) if p['player_id'] in stats_map else 0,
                        'stumpings': int(stats_map[p['player_id']]['stumpings']) if p['player_id'] in stats_map else 0,
                        'balls_bowled': int(stats_map[p['player_id']]['balls_bowled']) if p['player_id'] in stats_map else 0,
                        'runs_conceded': int(stats_map[p['player_id']]['runs_conceded']) if p['player_id'] in stats_map else 0,
                        'maidens': int(stats_map[p['player_id']]['maidens']) if p['player_id'] in stats_map else 0,
                        'run_outs_direct': int(stats_map[p['player_id']]['run_outs_direct']) if p['player_id'] in stats_map else 0,
                        'run_outs_indirect': int(stats_map[p['player_id']]['run_outs_indirect']) if p['player_id'] in stats_map else 0,
                        'is_dismissed': bool(stats_map[p['player_id']]['is_dismissed']) if p['player_id'] in stats_map else False,
                        'duck': bool(stats_map[p['player_id']]['is_duck']) if p['player_id'] in stats_map else False,
                    } if p['player_id'] in stats_map else None,
                }
                for p in players
            ],
        }
    finally:
        cursor.close()
        conn.close()


@fantasy_router.get('/matches/{match_id}/points')
async def get_match_points_breakdown(
    match_id: int,
    authorization: Optional[str] = Header(None)
):
    """Get per-player stats breakdown for the current user's team in a match."""
    from app import get_current_user
    current_user = await get_current_user(authorization)
    user_id = current_user['user_id']

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Get user's selection
        cursor.execute(
            'SELECT id FROM fantasy_user_selections WHERE user_id = %s AND match_id = %s',
            (user_id, match_id)
        )
        sel = cursor.fetchone()
        if not sel:
            return {'breakdown': []}

        cursor.execute(
            '''SELECT
                 futp.player_id, futp.is_captain, futp.is_vice_captain,
                 p.name, p.role, p.image_url,
                 t.short_name AS team_short,
                 COALESCE(fpms.runs_scored, 0) AS runs_scored,
                 COALESCE(fpms.balls_faced, 0) AS balls_faced,
                 COALESCE(fpms.fours, 0) AS fours,
                 COALESCE(fpms.sixes, 0) AS sixes,
                 COALESCE(fpms.wickets, 0) AS wickets,
                 COALESCE(fpms.catches, 0) AS catches,
                 COALESCE(fpms.stumpings, 0) AS stumpings,
                 COALESCE(fpms.fantasy_points, 0) AS base_points
               FROM fantasy_user_team_players futp
               JOIN fantasy_ipl_players p ON futp.player_id = p.id
               JOIN fantasy_ipl_teams t ON p.team_id = t.id
               LEFT JOIN fantasy_player_match_stats fpms
                 ON fpms.player_id = futp.player_id AND fpms.match_id = %s
               WHERE futp.selection_id = %s''',
            (match_id, sel['id'])
        )
        rows = cursor.fetchall()
        breakdown = []
        for r in rows:
            base = float(r['base_points'])
            multiplier = 2.0 if r['is_captain'] else 1.5 if r['is_vice_captain'] else 1.0
            breakdown.append({
                'player_id': r['player_id'],
                'name': r['name'],
                'role': r['role'],
                'image_url': r['image_url'],
                'team_short': r['team_short'],
                'is_captain': bool(r['is_captain']),
                'is_vice_captain': bool(r['is_vice_captain']),
                'stats': {
                    'runs': r['runs_scored'],
                    'balls': r['balls_faced'],
                    'fours': r['fours'],
                    'sixes': r['sixes'],
                    'wickets': r['wickets'],
                    'catches': r['catches'],
                    'stumpings': r['stumpings'],
                },
                'base_points': base,
                'multiplier': multiplier,
                'total_points': round(base * multiplier, 2),
            })
        return {'breakdown': breakdown}
    finally:
        cursor.close()
        conn.close()


@fantasy_router.get('/matches/{match_id}/player-scores')
async def get_match_player_scores(match_id: int):
    """Get all players who scored points in a match, sorted by points desc."""
    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            '''SELECT fms.id, fms.match_name, fms.status
               FROM fantasy_match_schedule fms
               WHERE fms.id = %s''',
            (match_id,)
        )
        match = cursor.fetchone()
        if not match:
            raise HTTPException(status_code=404, detail='Match not found')

        cursor.execute(
            '''SELECT
                 fpms.player_id,
                 p.name,
                 p.role,
                 p.image_url,
                 t.short_name AS team_short,
                 t.primary_color AS team_color,
                 COALESCE(fpms.runs_scored, 0) AS runs_scored,
                 COALESCE(fpms.balls_faced, 0) AS balls_faced,
                 COALESCE(fpms.fours, 0) AS fours,
                 COALESCE(fpms.sixes, 0) AS sixes,
                 COALESCE(fpms.wickets, 0) AS wickets,
                 COALESCE(fpms.catches, 0) AS catches,
                 COALESCE(fpms.stumpings, 0) AS stumpings,
                 COALESCE(fpms.fantasy_points, 0) AS base_points
               FROM fantasy_player_match_stats fpms
               JOIN fantasy_ipl_players p ON fpms.player_id = p.id
               JOIN fantasy_ipl_teams t ON p.team_id = t.id
               WHERE fpms.match_id = %s AND fpms.fantasy_points > 0
               ORDER BY fpms.fantasy_points DESC''',
            (match_id,)
        )
        players = []
        for r in cursor.fetchall():
            players.append({
                'player_id': r['player_id'],
                'name': r['name'],
                'role': r['role'],
                'image_url': r['image_url'],
                'team_short': r['team_short'],
                'team_color': r['team_color'],
                'stats': {
                    'runs': int(r['runs_scored']),
                    'balls': int(r['balls_faced']),
                    'fours': int(r['fours']),
                    'sixes': int(r['sixes']),
                    'wickets': int(r['wickets']),
                    'catches': int(r['catches']),
                    'stumpings': int(r['stumpings']),
                },
                'base_points': float(r['base_points']),
            })
        return {
            'players': players,
            'match': {
                'id': match['id'],
                'name': match['match_name'],
                'status': match['status'],
            },
        }
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# OVERALL FANTASY LEADERBOARD
# ============================================================================

@fantasy_router.get('/leaderboard')
async def get_overall_fantasy_leaderboard(
    authorization: Optional[str] = Header(None),
    series_id: Optional[int] = Query(None, description='Scope leaderboard to a specific series'),
):
    """
    Overall fantasy leaderboard aggregated across completed matches.
    Optionally scoped to a series via ?series_id=.
    Applies F1-style points to each user's finishing rank per match:
      P1=25, P2=18, P3=15, P4=12, P5=10, P6=8, P7=6, P8=4, P9=2, P10=1, rest=0
    """
    current_user_id = None
    if authorization:
        try:
            from app import get_current_user
            user = await get_current_user(authorization)
            current_user_id = user['user_id']
        except Exception:
            pass

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        series_filter = 'AND fms.series_id = %(series_id)s' if series_id is not None else ''
        params = {'series_id': series_id} if series_id is not None else {}
        cursor.execute(f"""
            SELECT
                u.id AS user_id,
                u.display_name,
                u.profile_picture,
                SUM(
                    CASE fml.rank
                        WHEN 1  THEN 25
                        WHEN 2  THEN 18
                        WHEN 3  THEN 15
                        WHEN 4  THEN 12
                        WHEN 5  THEN 10
                        WHEN 6  THEN 8
                        WHEN 7  THEN 6
                        WHEN 8  THEN 4
                        WHEN 9  THEN 2
                        WHEN 10 THEN 1
                        ELSE 0
                    END
                ) AS total_points,
                COUNT(fml.id) AS matches_played,
                MIN(fml.rank) AS best_rank,
                ROUND(
                    SUM(
                        CASE fml.rank
                            WHEN 1  THEN 25
                            WHEN 2  THEN 18
                            WHEN 3  THEN 15
                            WHEN 4  THEN 12
                            WHEN 5  THEN 10
                            WHEN 6  THEN 8
                            WHEN 7  THEN 6
                            WHEN 8  THEN 4
                            WHEN 9  THEN 2
                            WHEN 10 THEN 1
                            ELSE 0
                        END
                    ) / COUNT(fml.id), 1
                ) AS average_points
            FROM users u
            INNER JOIN fantasy_match_leaderboard fml ON fml.user_id = u.id
            INNER JOIN fantasy_match_schedule fms ON fms.id = fml.match_id
                AND fms.status = 'completed'
                {series_filter}
            GROUP BY u.id, u.display_name, u.profile_picture
            ORDER BY total_points DESC, best_rank ASC, u.display_name ASC
        """, params)

        rows = cursor.fetchall()

        def _pic(row):
            pp = row.get('profile_picture')
            if pp is None:
                return None
            return pp.decode('utf-8') if isinstance(pp, bytes) else pp

        leaderboard = [
            {
                'user_id': row['user_id'],
                'display_name': row['display_name'],
                'profilePicture': _pic(row),
                'total_points': int(row['total_points']),
                'matches_played': int(row['matches_played']),
                'average_points': float(row['average_points']),
                'best_rank': int(row['best_rank']) if row['best_rank'] else None,
                'is_current_user': row['user_id'] == current_user_id,
            }
            for row in rows
        ]
        return {'leaderboard': leaderboard}
    finally:
        cursor.close()
        conn.close()


@fantasy_router.get('/players/{user_id}/matches')
async def get_fantasy_player_matches(
    user_id: int,
    series_id: Optional[int] = Query(None, description='Scope match history to a specific series'),
):
    """
    Fantasy match history for a specific user across completed matches.
    Optionally scoped to a series via ?series_id=.
    """
    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        series_filter = 'AND fms.series_id = %(series_id)s' if series_id is not None else ''
        params = {'user_id': user_id, 'series_id': series_id} if series_id is not None else {'user_id': user_id}
        cursor.execute(f"""
            SELECT
                fms.id          AS match_id,
                fms.match_name,
                fms.short_name,
                fms.match_date,
                fml.rank,
                fml.total_points AS fantasy_points,
                CASE fml.rank
                    WHEN 1  THEN 25
                    WHEN 2  THEN 18
                    WHEN 3  THEN 15
                    WHEN 4  THEN 12
                    WHEN 5  THEN 10
                    WHEN 6  THEN 8
                    WHEN 7  THEN 6
                    WHEN 8  THEN 4
                    WHEN 9  THEN 2
                    WHEN 10 THEN 1
                    ELSE 0
                END AS points_earned
            FROM fantasy_match_leaderboard fml
            INNER JOIN fantasy_match_schedule fms ON fms.id = fml.match_id
                AND fms.status = 'completed'
                {series_filter}
            WHERE fml.user_id = %(user_id)s
            ORDER BY fms.match_date DESC, fms.id DESC
        """, params)

        rows = cursor.fetchall()
        matches = [
            {
                'match_id': r['match_id'],
                'match_name': r['match_name'],
                'short_name': r['short_name'],
                'match_date': r['match_date'].isoformat() if r['match_date'] else None,
                'rank': int(r['rank']),
                'fantasy_points': float(r['fantasy_points']),
                'points_earned': int(r['points_earned']),
            }
            for r in rows
        ]
        return {'matches': matches}
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@fantasy_router.get('/admin/series')
async def admin_get_series(
    authorization: Optional[str] = Header(None)
):
    """Admin: List all series with match counts."""
    from app import verify_admin
    await verify_admin(authorization)

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            '''SELECT fs.id, fs.name, fs.cricapi_series_id, fs.is_active, fs.created_at,
                      COUNT(fms.id) AS match_count
               FROM fantasy_series fs
               LEFT JOIN fantasy_match_schedule fms ON fms.series_id = fs.id
               GROUP BY fs.id, fs.name, fs.cricapi_series_id, fs.is_active, fs.created_at
               ORDER BY fs.id ASC'''
        )
        series = [
            {
                'id': r['id'],
                'name': r['name'],
                'cricapi_series_id': r['cricapi_series_id'],
                'is_active': bool(r['is_active']),
                'match_count': int(r['match_count']),
                'created_at': r['created_at'].isoformat() if r['created_at'] else None,
            }
            for r in cursor.fetchall()
        ]
        return {'series': series}
    finally:
        cursor.close()
        conn.close()


@fantasy_router.post('/admin/series')
async def admin_create_series(
    request: SeriesCreate,
    authorization: Optional[str] = Header(None)
):
    """Admin: Create a new series."""
    from app import verify_admin
    await verify_admin(authorization)

    conn = _get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO fantasy_series (name, cricapi_series_id) VALUES (%s, %s)',
            (request.name.strip(), request.cricapi_series_id.strip())
        )
        conn.commit()
        new_id = cursor.lastrowid
        return {'id': new_id, 'message': f'Series "{request.name}" created successfully'}
    except Exception as e:
        conn.rollback()
        if 'Duplicate' in str(e):
            raise HTTPException(status_code=409, detail='A series with that CricAPI series ID already exists')
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@fantasy_router.put('/admin/series/{series_id}')
async def admin_update_series(
    series_id: int,
    request: SeriesUpdate,
    authorization: Optional[str] = Header(None)
):
    """Admin: Update series name or active status."""
    from app import verify_admin
    await verify_admin(authorization)

    fields, values = [], []
    if request.name is not None:
        fields.append('name = %s')
        values.append(request.name.strip())
    if request.is_active is not None:
        fields.append('is_active = %s')
        values.append(1 if request.is_active else 0)

    if not fields:
        raise HTTPException(status_code=400, detail='No fields to update')

    conn = _get_db()
    cursor = conn.cursor()
    try:
        values.append(series_id)
        cursor.execute(
            f'UPDATE fantasy_series SET {", ".join(fields)} WHERE id = %s',
            values
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail='Series not found')
        conn.commit()
        return {'message': 'Series updated successfully'}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@fantasy_router.get('/admin/players')
async def admin_get_players(
    authorization: Optional[str] = Header(None)
):
    """Admin: List all players with credits and team info."""
    from app import verify_admin
    await verify_admin(authorization)

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            '''SELECT p.id, p.cricapi_player_id, p.name, p.role, p.credits, p.is_active,
                      p.batting_style, p.bowling_style, p.country, p.image_url,
                      t.short_name AS team_short, t.full_name AS team_name, t.id AS team_id
               FROM fantasy_ipl_players p
               JOIN fantasy_ipl_teams t ON p.team_id = t.id
               ORDER BY t.short_name, p.role, p.name'''
        )
        players = []
        for r in cursor.fetchall():
            players.append({
                'id': r['id'],
                'cricapi_player_id': r['cricapi_player_id'],
                'name': r['name'],
                'role': r['role'],
                'credits': float(r['credits']),
                'is_active': bool(r['is_active']),
                'batting_style': r['batting_style'],
                'bowling_style': r['bowling_style'],
                'country': r['country'],
                'image_url': r['image_url'],
                'team_id': r['team_id'],
                'team_short': r['team_short'],
                'team_name': r['team_name'],
            })
        return {'players': players}
    finally:
        cursor.close()
        conn.close()


@fantasy_router.put('/admin/players/{player_id}')
async def admin_update_player(
    player_id: int,
    update: PlayerCreditUpdate,
    authorization: Optional[str] = Header(None)
):
    """Admin: Update player credits, role, or active status."""
    from app import verify_admin
    await verify_admin(authorization)

    if update.role and update.role not in ('WK', 'BAT', 'AR', 'BOWL'):
        raise HTTPException(status_code=400, detail='Invalid role. Must be WK, BAT, AR, or BOWL')
    if update.credits is not None and (update.credits < 5.0 or update.credits > 15.0):
        raise HTTPException(status_code=400, detail='Credits must be between 5.0 and 15.0')

    conn = _get_db()
    cursor = conn.cursor()
    try:
        parts = []
        params = []
        if update.credits is not None:
            parts.append('credits = %s')
            params.append(update.credits)
        if update.role is not None:
            parts.append('role = %s')
            params.append(update.role)
        if update.is_active is not None:
            parts.append('is_active = %s')
            params.append(int(update.is_active))
        if not parts:
            return {'message': 'No changes'}
        params.append(player_id)
        cursor.execute(f'UPDATE fantasy_ipl_players SET {", ".join(parts)} WHERE id = %s', params)
        conn.commit()
        return {'message': 'Player updated'}
    finally:
        cursor.close()
        conn.close()


@fantasy_router.get('/admin/api-usage')
async def admin_get_api_usage(authorization: Optional[str] = Header(None)):
    """Admin: Get today's API call usage."""
    from app import verify_admin
    await verify_admin(authorization)

    from fantasy_scheduler import get_api_calls_today
    calls_today = get_api_calls_today()
    return {
        'calls_today': calls_today,
        'daily_limit': 2000,
        'safety_limit': 1900,
        'remaining': max(0, 1900 - calls_today),
    }


@fantasy_router.post('/admin/trigger-sync')
async def admin_trigger_sync(authorization: Optional[str] = Header(None)):
    """Admin: Manually trigger a series_info sync."""
    from app import verify_admin
    await verify_admin(authorization)

    try:
        from fantasy_scheduler import fetch_series_info
        fetch_series_info()
        return {'message': 'Series sync completed'}
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Sync failed: {str(e)}')


@fantasy_router.post('/admin/trigger-squad/{match_id}')
async def admin_trigger_squad(
    match_id: int,
    authorization: Optional[str] = Header(None)
):
    """Admin: Manually trigger squad fetch for a specific match."""
    from app import verify_admin
    await verify_admin(authorization)

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            'SELECT id, cricapi_match_id FROM fantasy_match_schedule WHERE id = %s',
            (match_id,)
        )
        match = cursor.fetchone()
        if not match:
            raise HTTPException(status_code=404, detail='Match not found')
    finally:
        cursor.close()
        conn.close()

    try:
        from fantasy_scheduler import fetch_match_squad
        fetch_match_squad(match['cricapi_match_id'], match['id'])
        return {'message': f'Squad fetch triggered for match {match_id}'}
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Squad fetch failed: {str(e)}')


@fantasy_router.post('/admin/trigger-scorecard/{match_id}')
async def admin_trigger_scorecard(
    match_id: int,
    authorization: Optional[str] = Header(None)
):
    """Admin: Manually trigger scorecard + leaderboard update for a match."""
    from app import verify_admin
    await verify_admin(authorization)

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            'SELECT id, cricapi_match_id FROM fantasy_match_schedule WHERE id = %s',
            (match_id,)
        )
        match = cursor.fetchone()
        if not match:
            raise HTTPException(status_code=404, detail='Match not found')
    finally:
        cursor.close()
        conn.close()

    try:
        from fantasy_scheduler import fetch_live_scorecard
        fetch_live_scorecard(match['cricapi_match_id'], match['id'])
        return {'message': f'Scorecard fetch triggered for match {match_id}'}
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Scorecard fetch failed: {str(e)}')


@fantasy_router.get('/admin/matches')
async def admin_get_matches(authorization: Optional[str] = Header(None)):
    """Admin: List all matches with sync status."""
    from app import verify_admin
    await verify_admin(authorization)

    conn = _get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            '''SELECT
                 fms.id, fms.match_name, fms.status, fms.match_date,
                 fms.match_datetime_gmt, fms.squad_fetched, fms.scorecard_fetched,
                 fms.last_synced_at,
                 t1.short_name AS team1_short,
                 t2.short_name AS team2_short
               FROM fantasy_match_schedule fms
               LEFT JOIN fantasy_ipl_teams t1 ON fms.team1_id = t1.id
               LEFT JOIN fantasy_ipl_teams t2 ON fms.team2_id = t2.id
               ORDER BY fms.match_datetime_gmt ASC, fms.match_date ASC'''
        )
        matches = [
            {
                'id': r['id'],
                'match_name': r['match_name'],
                'status': r['status'],
                'match_date': r['match_date'].isoformat() if r['match_date'] else None,
                'match_datetime_gmt': r['match_datetime_gmt'].isoformat() if r['match_datetime_gmt'] else None,
                'squad_fetched': bool(r['squad_fetched']),
                'scorecard_fetched': bool(r['scorecard_fetched']),
                'last_synced_at': r['last_synced_at'].isoformat() if r['last_synced_at'] else None,
                'team1_short': r['team1_short'],
                'team2_short': r['team2_short'],
            }
            for r in cursor.fetchall()
        ]
        return {'matches': matches}
    finally:
        cursor.close()
        conn.close()
