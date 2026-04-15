"""
Fantasy Cricket Data Loader & Scheduler
Fetches data from CricketData.org API and keeps the DB up to date.

API call budget: 2000/day. This scheduler targets ~100 calls/day peak.
Schedule:
  - series_info: 2x/day  (00:00 + 12:00 UTC)
  - check_and_fetch_squads: every 30 min (fetches squad ~2.5hrs before match start)
  - update_live_matches: every 5 min (only if live matches exist)
"""

import os
import re
import json
import logging
import threading
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional

import mysql.connector
from apscheduler.schedulers.background import BackgroundScheduler

from fantasy_points import (
    calculate_player_points,
    apply_captain_vc_multipliers,
    parse_scorecard_batting,
    parse_scorecard_bowling,
)

logger = logging.getLogger(__name__)

CRICAPI_BASE = 'https://api.cricapi.com/v1'
IPL_SERIES_ID = os.getenv('FANTASY_IPL_SERIES_ID', '87c62aac-bc3c-4738-ab93-19da0690488f')
DAILY_API_LIMIT = 10000
DAILY_API_SAFETY_LIMIT = 9500  # Stop early to preserve buffer

# Module-level block flag — set when API returns "Blocked for X minutes"
_api_blocked_until: Optional[datetime] = None


def _get_api_key():
    key = os.getenv('CRICKETDATA_API_KEY')
    if not key:
        raise RuntimeError('CRICKETDATA_API_KEY environment variable not set')
    return key


def _get_db_config():
    return {
        'host': os.getenv('DB_HOST'),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'port': int(os.getenv('DB_PORT', 3306))
    }


def get_db_connection():
    return mysql.connector.connect(**_get_db_config())


# ============================================================================
# API CALL COUNTER
# ============================================================================

def get_api_calls_today() -> int:
    """Return how many API calls have been made today (UTC)."""
    today = datetime.now(timezone.utc).date()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            'SELECT calls_made FROM fantasy_api_call_log WHERE call_date = %s',
            (today,)
        )
        row = cursor.fetchone()
        return row['calls_made'] if row else 0
    finally:
        cursor.close()
        conn.close()


def increment_api_counter(n: int = 1, call_type: str = 'unknown'):
    """Increment the daily API call counter. Raises RuntimeError if over safety limit."""
    today = datetime.now(timezone.utc).date()
    current = get_api_calls_today()
    if current + n > DAILY_API_SAFETY_LIMIT:
        raise RuntimeError(
            f'API safety limit reached: {current} used today, adding {n} would exceed {DAILY_API_SAFETY_LIMIT}.'
        )
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''INSERT INTO fantasy_api_call_log (call_date, calls_made, last_call_type)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 calls_made = calls_made + %s,
                 last_call_type = %s,
                 updated_at = CURRENT_TIMESTAMP''',
            (today, n, call_type, n, call_type)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def _cricapi_get(endpoint: str, params: dict) -> Optional[dict]:
    """Make a GET request to CricketData API. Returns parsed JSON or None on error."""
    global _api_blocked_until
    # Check temporary block flag
    if _api_blocked_until and datetime.now(timezone.utc) < _api_blocked_until:
        print(f'[fantasy] Skipping {endpoint} — API blocked until {_api_blocked_until.strftime("%H:%M UTC")}')
        return None
    try:
        params['apikey'] = _get_api_key()
        params['offset'] = params.get('offset', 0)
        increment_api_counter(1, endpoint)
        resp = requests.get(f'{CRICAPI_BASE}/{endpoint}', params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Sync our counter with the API's own hitsToday if provided
        api_info = data.get('info', {})
        if api_info.get('hitsToday') is not None:
            _sync_counter_from_api(api_info['hitsToday'], api_info.get('hitsLimit'))

        if data.get('status') != 'success':
            reason = data.get('reason', '')
            print(f'[fantasy] CricketData non-success for {endpoint}: {data.get("status")} {reason}')
            # Set temp block if API says we're blocked or limit exceeded
            if 'block' in reason.lower() or 'exceeded' in reason.lower():
                _api_blocked_until = datetime.now(timezone.utc) + timedelta(minutes=20)
                print(f'[fantasy] API blocked — pausing all calls for 20 min until {_api_blocked_until.strftime("%H:%M UTC")}')
            logger.warning('CricketData API returned non-success for %s: %s', endpoint, data)
            return None
        _api_blocked_until = None  # Clear block flag on success
        return data
    except RuntimeError as e:
        logger.error('API counter/key error for %s: %s', endpoint, e)
        print(f'[fantasy] API budget exhausted for {endpoint}: {e}')
        return None
    except requests.RequestException as e:
        logger.error('CricketData API request failed (%s): %s', endpoint, e)
        print(f'[fantasy] HTTP error for {endpoint}: {e}')
        return None


def _sync_counter_from_api(hits_today: int, hits_limit: int = None):
    """
    Update our local counter to reflect what the API reports as hitsToday.
    If hits_today is at/near hits_limit, set _api_blocked_until for the rest of the UTC day.
    NEVER inflate the DB counter — the GREATEST logic in the upsert would lock us out forever.
    """
    global _api_blocked_until
    today = datetime.now(timezone.utc).date()
    if hits_limit and hits_today >= hits_limit:
        # Block until start of next UTC day
        tomorrow_utc = datetime.combine(
            today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
        )
        _api_blocked_until = tomorrow_utc
        print(f'[fantasy] API plan limit reached ({hits_today}/{hits_limit}). Blocking until {tomorrow_utc.strftime("%Y-%m-%d 00:00 UTC")}')
    # Write actual hitsToday to DB — NEVER inflate to DAILY_API_SAFETY_LIMIT
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''INSERT INTO fantasy_api_call_log (call_date, calls_made, last_call_type)
               VALUES (%s, %s, 'api_sync')
               ON DUPLICATE KEY UPDATE
                 calls_made = GREATEST(calls_made, %s),
                 updated_at = CURRENT_TIMESTAMP''',
            (today, hits_today, hits_today)
        )
        conn.commit()
    except Exception:
        pass
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# DATE / TIME HELPERS
# ============================================================================

_STATUS_TIME_RE = re.compile(r'(\d{1,2}):(\d{2})\s*(?:GMT|UTC)', re.IGNORECASE)


def _parse_match_time_from_status(status_note: str) -> Optional[tuple]:
    """
    Try to extract UTC time from a status note like 'Match starts at Apr 17, 14:00 GMT'.
    Returns (hour, minute) tuple or None if not found.
    """
    if not status_note:
        return None
    m = _STATUS_TIME_RE.search(status_note)
    if m:
        try:
            return int(m.group(1)), int(m.group(2))
        except ValueError:
            pass
    return None


# ============================================================================
# TEAM RESOLUTION
# ============================================================================

def _resolve_team_id(cursor, team_name: str) -> Optional[int]:
    """
    Find a fantasy_ipl_teams.id by matching cricapi_team_name.
    Tries exact match first, then a startswith match.
    """
    if not team_name:
        return None
    cursor.execute(
        'SELECT id FROM fantasy_ipl_teams WHERE cricapi_team_name = %s LIMIT 1',
        (team_name,)
    )
    row = cursor.fetchone()
    if row:
        return row['id'] if isinstance(row, dict) else row[0]
    # Fuzzy: check if any stored name is a prefix of the incoming name or vice versa
    cursor.execute('SELECT id, cricapi_team_name FROM fantasy_ipl_teams')
    all_teams = cursor.fetchall()
    name_lower = team_name.lower()
    for t in all_teams:
        tid = t['id'] if isinstance(t, dict) else t[0]
        stored = (t['cricapi_team_name'] if isinstance(t, dict) else t[1]).lower()
        if stored in name_lower or name_lower in stored:
            return tid
    return None


# ============================================================================
# SERIES SYNC
# ============================================================================

def fetch_series_info():
    """
    Fetch IPL 2026 series info and upsert all matches into fantasy_match_schedule.
    Recommended max: 2-3 times per day.
    API cost: 1 call.
    """
    logger.info('fetch_series_info: starting')
    print('[fantasy] fetch_series_info: calling API...')
    data = _cricapi_get('series_info', {'id': IPL_SERIES_ID})
    if not data:
        print('[fantasy] fetch_series_info: no data returned from API')
        return

    match_list = data.get('data', {}).get('matchList', [])
    logger.info('fetch_series_info: found %d matches', len(match_list))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        for m in match_list:
            match_id = m.get('id')
            if not match_id:
                continue

            match_name = m.get('name', '')
            match_type = m.get('matchType', 't20')
            datetime_gmt_str = m.get('dateTimeGMT', '')
            date_only_str = m.get('date', '')

            # Parse dates — prefer dateTimeGMT (has correct time), fall back to date
            match_date = None
            match_datetime_gmt = None
            if datetime_gmt_str:
                try:
                    dt = datetime.fromisoformat(datetime_gmt_str.replace('Z', '+00:00'))
                    match_date = dt.date()
                    match_datetime_gmt = dt.replace(tzinfo=None)  # Store as naive UTC
                except ValueError:
                    pass
            if not match_date and date_only_str:
                try:
                    match_date = datetime.strptime(date_only_str[:10], '%Y-%m-%d').date()
                except ValueError:
                    pass

            venue = m.get('venue')

            # Determine status
            status_raw = m.get('status', '')
            ms = m.get('matchStarted', False)
            me = m.get('matchEnded', False)
            if me or 'won' in status_raw.lower() or 'tied' in status_raw.lower() or 'abandoned' in status_raw.lower():
                status = 'completed'
            elif ms:
                status = 'live'
            else:
                status = 'upcoming'

            # If datetime has midnight time (00:00:00), the API only gave us a date.
            # Try to extract the actual kick-off time from the status note, e.g.
            # "Match starts at Apr 17, 14:00 GMT".  Fall back to 14:00 GMT.
            if match_datetime_gmt and match_datetime_gmt.hour == 0 and match_datetime_gmt.minute == 0:
                parsed = _parse_match_time_from_status(status_raw)
                if parsed:
                    match_datetime_gmt = match_datetime_gmt.replace(hour=parsed[0], minute=parsed[1])
                elif status == 'upcoming':
                    match_datetime_gmt = match_datetime_gmt.replace(hour=14, minute=0)
            elif match_date and not match_datetime_gmt:
                # We have a date but no datetime at all — build one from status_note or default
                parsed = _parse_match_time_from_status(status_raw)
                hour, minute = parsed if parsed else (14, 0)
                match_datetime_gmt = datetime.combine(match_date, datetime.min.time()).replace(hour=hour, minute=minute)

            # Resolve team IDs from teams array
            teams = m.get('teams', [])
            team1_id = _resolve_team_id(cursor, teams[0] if len(teams) > 0 else None)
            team2_id = _resolve_team_id(cursor, teams[1] if len(teams) > 1 else None)

            # Build short name
            short_parts = match_name.split(',')[0] if match_name else match_name

            # Capture current score (available for live/completed matches)
            score_raw = m.get('score', [])
            live_score_json = json.dumps(score_raw) if score_raw else None

            cursor.execute(
                '''INSERT INTO fantasy_match_schedule
                   (cricapi_match_id, match_name, short_name, team1_id, team2_id,
                    match_date, match_datetime_gmt, venue, match_type, status, status_note, live_score, last_synced_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                   ON DUPLICATE KEY UPDATE
                     match_name = VALUES(match_name),
                     short_name = VALUES(short_name),
                     team1_id = COALESCE(VALUES(team1_id), team1_id),
                     team2_id = COALESCE(VALUES(team2_id), team2_id),
                     match_date = VALUES(match_date),
                     match_datetime_gmt = VALUES(match_datetime_gmt),
                     venue = VALUES(venue),
                     match_type = VALUES(match_type),
                     status = VALUES(status),
                     status_note = VALUES(status_note),
                     live_score = COALESCE(VALUES(live_score), live_score),
                     last_synced_at = NOW()''',
                (match_id, match_name, short_parts, team1_id, team2_id,
                 match_date, match_datetime_gmt, venue, match_type, status, status_raw, live_score_json)
            )
        conn.commit()
        logger.info('fetch_series_info: upserted %d matches', len(match_list))
        print(f'[fantasy] fetch_series_info: upserted {len(match_list)} matches')
    except Exception as e:
        logger.error('fetch_series_info DB error: %s', e)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# SQUAD SYNC
# ============================================================================

def fetch_match_squad(cricapi_match_id: str, db_match_id: int):
    """
    Fetch squad for a specific match and upsert players + squad entries.
    API cost: 1 call.
    """
    logger.info('fetch_match_squad: match %s', cricapi_match_id)
    data = _cricapi_get('match_squad', {'id': cricapi_match_id})
    if not data:
        return

    teams_data = data.get('data', [])
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    players_added = 0
    try:
        for team_entry in teams_data:
            team_name = team_entry.get('teamName', '')
            team_id = _resolve_team_id(cursor, team_name)
            players = team_entry.get('players', [])

            xi_count = 0  # Track how many players are confirmed in playing XI for this team

            for p in players:
                pid = p.get('id')
                if not pid:
                    continue
                name = p.get('name', '')
                role_raw = (p.get('role') or '').strip()

                # Map API role to our ENUM
                role = _map_role(role_raw)

                batting_style = p.get('battingStyle') or p.get('batting_style')
                bowling_style = p.get('bowlingStyle') or p.get('bowling_style')
                country = p.get('country')

                # Detect if player is in playing XI (only set after the toss)
                is_playing_xi = 1 if (
                    p.get('playing11') is True
                    or p.get('isPlaying') is True
                    or str(p.get('playing', '')).lower() == 'true'
                ) else 0
                if is_playing_xi:
                    xi_count += 1

                if team_id:
                    cursor.execute(
                        '''INSERT INTO fantasy_ipl_players
                           (cricapi_player_id, name, team_id, role, batting_style, bowling_style, country)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                             name = VALUES(name),
                             team_id = VALUES(team_id),
                             role = VALUES(role),
                             batting_style = COALESCE(VALUES(batting_style), batting_style),
                             bowling_style = COALESCE(VALUES(bowling_style), bowling_style),
                             country = COALESCE(VALUES(country), country),
                             updated_at = NOW()''',
                        (pid, name, team_id, role, batting_style, bowling_style, country)
                    )
                    conn.commit()

                # Get the player DB id
                cursor.execute(
                    'SELECT id FROM fantasy_ipl_players WHERE cricapi_player_id = %s', (pid,)
                )
                player_row = cursor.fetchone()
                if not player_row:
                    continue
                player_db_id = player_row['id']

                # Upsert into match squads, including playing XI status
                cursor.execute(
                    '''INSERT INTO fantasy_match_squads (match_id, player_id, is_announced, is_playing_xi)
                       VALUES (%s, %s, 1, %s)
                       ON DUPLICATE KEY UPDATE
                         is_announced = 1,
                         is_playing_xi = GREATEST(is_playing_xi, VALUES(is_playing_xi)),
                         updated_at = NOW()''',
                    (db_match_id, player_db_id, is_playing_xi)
                )
                players_added += 1

        # Mark squad as fetched ONLY if players were actually found
        if players_added > 0:
            # Check if any player across all teams is in playing XI
            any_xi = any(
                (p.get('playing11') is True
                 or p.get('isPlaying') is True
                 or str(p.get('playing', '')).lower() == 'true')
                for team_entry in teams_data
                for p in team_entry.get('players', [])
            )
            cursor.execute(
                '''UPDATE fantasy_match_schedule
                   SET squad_fetched = 1,
                       playing_xi_announced = CASE WHEN %s THEN 1 ELSE playing_xi_announced END,
                       last_synced_at = NOW()
                   WHERE id = %s''',
                (1 if any_xi else 0, db_match_id)
            )
            conn.commit()
            logger.info('fetch_match_squad: done for match db_id=%d (%d players, xi=%s)', db_match_id, players_added, any_xi)
            print(f'[fantasy] fetch_match_squad: match {db_match_id} → {players_added} players (XI announced: {any_xi})')
        else:
            print(f'[fantasy] fetch_match_squad: match {db_match_id} → no players returned, will retry')
    except Exception as e:
        logger.error('fetch_match_squad error: %s', e)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def _map_role(role_raw: str) -> str:
    role_lower = role_raw.lower()
    if 'keeper' in role_lower or 'wicket' in role_lower or 'wk' in role_lower:
        return 'WK'
    if 'all' in role_lower:
        return 'AR'
    if 'bowl' in role_lower:
        return 'BOWL'
    return 'BAT'


def promote_started_matches():
    """
    Promote matches from 'upcoming' to 'live' once their scheduled start time has passed.
    Runs every 5 minutes. No API calls — pure DB update.
    This ensures update_live_matches() can pick them up without waiting for the
    next fetch_series_info run (which only occurs twice per day).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''UPDATE fantasy_match_schedule
               SET status = 'live', last_synced_at = NOW()
               WHERE status = 'upcoming'
                 AND match_datetime_gmt IS NOT NULL
                 AND match_datetime_gmt <= UTC_TIMESTAMP()'''
        )
        promoted = cursor.rowcount
        conn.commit()
        if promoted:
            logger.info('promote_started_matches: promoted %d match(es) to live', promoted)
            print(f'[fantasy] promote_started_matches: promoted {promoted} match(es) to live')
    except Exception as e:
        logger.error('promote_started_matches error: %s', e)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def check_and_fetch_squads():
    """
    Fetch squads for ALL upcoming matches that haven't had their squad fetched yet.
    Runs every 30 minutes. Costs 1 API call per match without a squad.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            '''SELECT id, cricapi_match_id, match_name FROM fantasy_match_schedule
               WHERE squad_fetched = 0 AND status IN ('upcoming', 'live')
               ORDER BY match_datetime_gmt ASC'''
        )
        due = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if due:
        print(f'[fantasy] check_and_fetch_squads: {len(due)} matches need squads')
    for row in due:
        # Check budget before each call
        if get_api_calls_today() >= DAILY_API_SAFETY_LIMIT:
            print('[fantasy] check_and_fetch_squads: daily API limit reached, stopping')
            break
        try:
            fetch_match_squad(row['cricapi_match_id'], row['id'])
            time.sleep(1)  # 1-second pause between calls to avoid temp rate-limit blocks
        except Exception as e:
            logger.error('check_and_fetch_squads error for match %s: %s', row['cricapi_match_id'], e)


# ============================================================================
# LIVE SCORECARD SYNC
# ============================================================================

def fetch_live_scorecard(cricapi_match_id: str, db_match_id: int):
    """
    Fetch scorecard for a live/completed match, update player stats and recalculate leaderboard.
    API cost: 1 call.
    """
    logger.info('fetch_live_scorecard: match %s', cricapi_match_id)
    data = _cricapi_get('match_scorecard', {'id': cricapi_match_id})
    if not data:
        return

    match_data = data.get('data', {})
    scorecard = match_data.get('scorecard', [])

    # Determine if match ended
    match_ended = match_data.get('matchEnded', False)
    status_note = match_data.get('status', '')
    if match_ended or 'won' in status_note.lower() or 'tied' in status_note.lower():
        new_status = 'completed'
    else:
        new_status = 'live'

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Collect all batting and bowling stats per player (across both innings)
        # key: cricapi_player_id -> aggregated stats dict
        player_stats: dict[str, dict] = {}

        for innings in scorecard:
            batting = innings.get('batting', [])
            bowling = innings.get('bowling', [])

            for b in batting:
                # API structure: {'batsman': {'id': '...', 'name': '...'}, 'r': ..., ...}
                pid = (b.get('batsman') or {}).get('id') or b.get('id') or b.get('batsmanId')
                if not pid:
                    continue
                parsed = parse_scorecard_batting(b)
                if pid not in player_stats:
                    player_stats[pid] = _empty_stats()
                # Store player name for auto-upsert if not in DB
                player_stats[pid]['_name'] = (b.get('batsman') or {}).get('name', '')
                _merge_batting(player_stats[pid], parsed)

            for bw in bowling:
                # API structure: {'bowler': {'id': '...', 'name': '...'}, 'o': ..., ...}
                pid = (bw.get('bowler') or {}).get('id') or bw.get('id') or bw.get('bowlerId')
                if not pid:
                    continue
                parsed = parse_scorecard_bowling(bw)
                if pid not in player_stats:
                    player_stats[pid] = _empty_stats()
                player_stats[pid]['_name'] = (bw.get('bowler') or {}).get('name', '')
                _merge_bowling(player_stats[pid], parsed)

        # Upsert stats for each player into fantasy_player_match_stats
        for cricapi_pid, stats in player_stats.items():
            cursor.execute(
                'SELECT id FROM fantasy_ipl_players WHERE cricapi_player_id = %s', (cricapi_pid,)
            )
            pr = cursor.fetchone()
            if not pr:
                # Auto-create player from scorecard if not in DB yet (e.g. team squad not pre-fetched)
                player_name = stats.get('_name', '')
                if not player_name:
                    continue
                cursor.execute(
                    '''INSERT IGNORE INTO fantasy_ipl_players (cricapi_player_id, name, role)
                       VALUES (%s, %s, 'BAT')''',
                    (cricapi_pid, player_name)
                )
                conn.commit()
                cursor.execute(
                    'SELECT id FROM fantasy_ipl_players WHERE cricapi_player_id = %s', (cricapi_pid,)
                )
                pr = cursor.fetchone()
                if not pr:
                    continue
            player_db_id = pr['id']

            # Calculate fantasy points
            stats['is_duck'] = (
                stats.get('runs_scored', 0) == 0 and
                stats.get('is_dismissed', False) and
                stats.get('did_bat', False)
            )
            pts = calculate_player_points(stats)

            cursor.execute(
                '''INSERT INTO fantasy_player_match_stats
                   (match_id, player_id, runs_scored, balls_faced, fours, sixes,
                    is_dismissed, is_duck, wickets, balls_bowled, runs_conceded, maidens,
                    catches, stumpings, run_outs_direct, run_outs_indirect,
                    did_bat, did_bowl, fantasy_points)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                     runs_scored = VALUES(runs_scored),
                     balls_faced = VALUES(balls_faced),
                     fours = VALUES(fours),
                     sixes = VALUES(sixes),
                     is_dismissed = VALUES(is_dismissed),
                     is_duck = VALUES(is_duck),
                     wickets = VALUES(wickets),
                     balls_bowled = VALUES(balls_bowled),
                     runs_conceded = VALUES(runs_conceded),
                     maidens = VALUES(maidens),
                     catches = VALUES(catches),
                     stumpings = VALUES(stumpings),
                     run_outs_direct = VALUES(run_outs_direct),
                     run_outs_indirect = VALUES(run_outs_indirect),
                     did_bat = VALUES(did_bat),
                     did_bowl = VALUES(did_bowl),
                     fantasy_points = VALUES(fantasy_points),
                     last_updated = NOW()''',
                (db_match_id, player_db_id,
                 stats['runs_scored'], stats['balls_faced'], stats['fours'], stats['sixes'],
                 stats['is_dismissed'], stats['is_duck'],
                 stats['wickets'], stats['balls_bowled'], stats['runs_conceded'], stats['maidens'],
                 stats['catches'], stats['stumpings'], stats['run_outs_direct'], stats['run_outs_indirect'],
                 stats['did_bat'], stats['did_bowl'], pts)
            )

        conn.commit()

        # Update match status and live score
        score_raw = match_data.get('score', [])
        live_score_json = json.dumps(score_raw) if score_raw else None
        cursor.execute(
            '''UPDATE fantasy_match_schedule
               SET status = %s, status_note = %s,
                   live_score = COALESCE(%s, live_score),
                   last_synced_at = NOW(),
                   scorecard_fetched = IF(%s = 'completed', 1, scorecard_fetched)
               WHERE id = %s''',
            (new_status, status_note, live_score_json, new_status, db_match_id)
        )
        conn.commit()

        # Recalculate leaderboard for this match
        recalculate_match_leaderboard(db_match_id, conn)

        logger.info('fetch_live_scorecard: done for match db_id=%d, status=%s', db_match_id, new_status)
    except Exception as e:
        logger.error('fetch_live_scorecard error: %s', e)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def _empty_stats() -> dict:
    return {
        'did_bat': False, 'runs_scored': 0, 'balls_faced': 0, 'fours': 0, 'sixes': 0,
        'is_dismissed': False, 'is_duck': False,
        'did_bowl': False, 'wickets': 0, 'balls_bowled': 0, 'runs_conceded': 0, 'maidens': 0,
        'catches': 0, 'stumpings': 0, 'run_outs_direct': 0, 'run_outs_indirect': 0,
    }


def _merge_batting(target: dict, parsed: dict):
    target['did_bat'] = True
    target['runs_scored'] += parsed.get('runs_scored', 0)
    target['balls_faced'] += parsed.get('balls_faced', 0)
    target['fours'] += parsed.get('fours', 0)
    target['sixes'] += parsed.get('sixes', 0)
    target['is_dismissed'] = parsed.get('is_dismissed', False)


def _merge_bowling(target: dict, parsed: dict):
    target['did_bowl'] = True
    target['wickets'] += parsed.get('wickets', 0)
    target['balls_bowled'] += parsed.get('balls_bowled', 0)
    target['runs_conceded'] += parsed.get('runs_conceded', 0)
    target['maidens'] += parsed.get('maidens', 0)


def update_live_matches():
    """
    Fetch scorecards for all currently live matches.
    Runs every 5 minutes but skips if there are no live matches.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, cricapi_match_id FROM fantasy_match_schedule WHERE status = 'live'"
        )
        live = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if not live:
        return

    for row in live:
        try:
            fetch_live_scorecard(row['cricapi_match_id'], row['id'])
        except Exception as e:
            logger.error('update_live_matches error for match %s: %s', row['cricapi_match_id'], e)


# ============================================================================
# LEADERBOARD RECALCULATION
# ============================================================================

def recalculate_match_leaderboard(match_id: int, conn=None):
    """
    Recompute fantasy_match_leaderboard for all users who have a team in this match.
    Uses the latest fantasy_points from fantasy_player_match_stats.
    """
    close_conn = conn is None
    if conn is None:
        conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)
    try:
        # Get all user selections for this match
        cursor.execute(
            'SELECT id, user_id FROM fantasy_user_selections WHERE match_id = %s',
            (match_id,)
        )
        selections = cursor.fetchall()

        # Get all current player stats for this match
        cursor.execute(
            'SELECT player_id, fantasy_points FROM fantasy_player_match_stats WHERE match_id = %s',
            (match_id,)
        )
        stats_rows = cursor.fetchall()
        base_points = {r['player_id']: float(r['fantasy_points']) for r in stats_rows}

        leaderboard_data = []  # (user_id, total_points, captain_id, vc_id)

        for sel in selections:
            # Get their players
            cursor.execute(
                '''SELECT player_id, is_captain, is_vice_captain
                   FROM fantasy_user_team_players
                   WHERE selection_id = %s''',
                (sel['id'],)
            )
            team_players = cursor.fetchall()

            total = apply_captain_vc_multipliers(team_players, base_points)
            captain_id = next((tp['player_id'] for tp in team_players if tp['is_captain']), None)
            vc_id = next((tp['player_id'] for tp in team_players if tp['is_vice_captain']), None)

            leaderboard_data.append((sel['user_id'], total, captain_id, vc_id))

        # Sort by total points descending to assign ranks
        leaderboard_data.sort(key=lambda x: x[1], reverse=True)

        for rank_idx, (user_id, total, captain_id, vc_id) in enumerate(leaderboard_data, start=1):
            cursor.execute(
                '''INSERT INTO fantasy_match_leaderboard
                   (match_id, user_id, total_points, rank, captain_player_id, vice_captain_player_id)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                     total_points = VALUES(total_points),
                     rank = VALUES(rank),
                     captain_player_id = VALUES(captain_player_id),
                     vice_captain_player_id = VALUES(vice_captain_player_id),
                     last_updated = NOW()''',
                (match_id, user_id, total, rank_idx, captain_id, vc_id)
            )

        conn.commit()
        logger.info('recalculate_match_leaderboard: done for match_id=%d, %d users', match_id, len(leaderboard_data))
    except Exception as e:
        logger.error('recalculate_match_leaderboard error: %s', e)
        conn.rollback()
    finally:
        cursor.close()
        if close_conn:
            conn.close()


# ============================================================================
# SCHEDULER SETUP
# ============================================================================

_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler():
    """Initialize and start the APScheduler background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone='UTC', daemon=True)

    # Fetch series info 2x per day
    _scheduler.add_job(
        fetch_series_info,
        trigger='cron',
        hour='0,12',
        minute=5,
        id='series_sync',
        replace_existing=True,
        misfire_grace_time=300,
    )

    # Check for upcoming matches needing squad fetch every 30 min
    _scheduler.add_job(
        check_and_fetch_squads,
        trigger='interval',
        minutes=30,
        id='squad_sync',
        replace_existing=True,
        misfire_grace_time=120,
    )

    # Promote upcoming matches to live once their start time has passed (every 5 min, no API cost)
    _scheduler.add_job(
        promote_started_matches,
        trigger='interval',
        minutes=5,
        id='status_transition',
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Update live match scorecards every 2 min
    _scheduler.add_job(
        update_live_matches,
        trigger='interval',
        minutes=2,
        id='live_sync',
        replace_existing=True,
        misfire_grace_time=60,
    )

    _scheduler.start()
    logger.info('Fantasy scheduler started.')

    # Run initial sync immediately in background so matches populate on startup
    threading.Thread(target=_initial_sync, daemon=True).start()


def _initial_sync():
    """Run once on startup to populate fantasy_match_schedule without waiting for cron."""
    try:
        print('[fantasy] _initial_sync: fetching series info on startup...')
        fetch_series_info()
        check_and_fetch_squads()
        print('[fantasy] _initial_sync: done.')
    except Exception as e:
        print(f'[fantasy] _initial_sync error: {e}')
        logger.error('_initial_sync error: %s', e)


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info('Fantasy scheduler stopped.')
