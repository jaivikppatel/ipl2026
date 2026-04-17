"""
Fantasy Cricket Data Loader & Scheduler
Fetches data from Statpal.io Cricket API v1 and keeps the DB up to date.

Schedule:
  - fetch_season_fixtures: 2x/day  (00:05 + 12:05 UTC)
  - check_and_fetch_lineups: every 30 min (re-syncs tournament squads)
  - promote_started_matches: every 5 min (no API call — pure DB time comparison)
  - update_live_matches: every 2 min (only if live matches exist)
"""

import os
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
)

logger = logging.getLogger(__name__)

STATPAL_BASE = 'https://statpal.io/api/v1'

# Module-level retry-after flag — set on 429 responses
_retry_after_until: Optional[datetime] = None


def _get_access_key() -> str:
    key = os.getenv('STATPAL_ACCESS_KEY')
    if not key:
        raise RuntimeError('STATPAL_ACCESS_KEY environment variable not set')
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
# API CALL COUNTER (informational daily log — no hard blocking)
# ============================================================================

def get_api_calls_today() -> int:
    """Return how many API calls have been logged today (UTC)."""
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


def _increment_api_counter(call_type: str = 'unknown'):
    """Increment the daily API call counter (best-effort; never blocks on failure)."""
    today = datetime.now(timezone.utc).date()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''INSERT INTO fantasy_api_call_log (call_date, calls_made, last_call_type)
               VALUES (%s, 1, %s)
               ON DUPLICATE KEY UPDATE
                 calls_made = calls_made + 1,
                 last_call_type = %s,
                 updated_at = CURRENT_TIMESTAMP''',
            (today, call_type, call_type)
        )
        conn.commit()
    except Exception:
        pass
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# STATPAL API CLIENT
# ============================================================================

def _statpal_get(path: str, params: dict = None) -> Optional[dict]:
    """
    Make a GET request to Statpal.io Cricket API v1.
    Handles 429 rate-limit with a 65-second backoff (one retry).
    Returns parsed JSON or None on error.
    """
    global _retry_after_until

    if _retry_after_until and datetime.now(timezone.utc) < _retry_after_until:
        wait = (_retry_after_until - datetime.now(timezone.utc)).total_seconds()
        print(f'[fantasy] Rate-limited — waiting {wait:.0f}s before {path}')
        time.sleep(max(0, wait))

    if params is None:
        params = {}

    request_params = dict(params)
    request_params['access_key'] = _get_access_key()
    url = f'{STATPAL_BASE}/{path.lstrip("/")}'
    _increment_api_counter(path)

    for attempt in range(2):
        try:
            resp = requests.get(url, params=request_params, timeout=20)
            if resp.status_code == 429:
                backoff = 65
                _retry_after_until = datetime.now(timezone.utc) + timedelta(seconds=backoff)
                print(f'[fantasy] 429 rate-limited on {path} — backing off {backoff}s (attempt {attempt + 1})')
                if attempt == 0:
                    time.sleep(backoff)
                    continue
                return None
            resp.raise_for_status()
            _retry_after_until = None
            return resp.json()
        except requests.RequestException as e:
            logger.error('Statpal API request failed (%s): %s', path, e)
            print(f'[fantasy] HTTP error for {path}: {e}')
            return None

    return None


# ============================================================================
# FIXTURE STATUS MAPPING
# ============================================================================

def _map_status(statpal_status: str) -> str:
    """Map a Statpal match status string to our internal status ENUM."""
    s = (statpal_status or '').strip()
    if s in ('Finished', 'Completed', 'Result'):
        return 'completed'
    if s in ('Cancelled', 'Abandoned', 'No Result'):
        return 'abandoned'
    if s in ('In Progress', 'Live', 'Innings Break', 'Lunch', 'Tea', 'Rain Delay', 'Delayed',
              'Toss', 'Pre-match', 'Prematch', 'About to begin', 'First Innings', 'Second Innings'):
        return 'live'
    return 'upcoming'


# ============================================================================
# TEAM RESOLUTION
# ============================================================================

def _resolve_team_id(cursor, statpal_team_id: Optional[int], team_name: str = None) -> Optional[int]:
    """
    Find a fantasy_ipl_teams.id by Statpal team ID first, then by name.
    When a name match succeeds, also persists the statpal_team_id for future lookups.
    """
    if statpal_team_id:
        cursor.execute(
            'SELECT id FROM fantasy_ipl_teams WHERE statpal_team_id = %s LIMIT 1',
            (statpal_team_id,)
        )
        row = cursor.fetchone()
        if row:
            return row['id'] if isinstance(row, dict) else row[0]

    if team_name:
        cursor.execute('SELECT id, team_name FROM fantasy_ipl_teams')
        all_teams = cursor.fetchall()
        name_lower = team_name.lower()
        for t in all_teams:
            tid = t['id'] if isinstance(t, dict) else t[0]
            stored = (t['team_name'] if isinstance(t, dict) else t[1]).lower()
            if stored == name_lower or stored in name_lower or name_lower in stored:
                if statpal_team_id:
                    try:
                        cursor.execute(
                            'UPDATE fantasy_ipl_teams SET statpal_team_id = %s WHERE id = %s',
                            (statpal_team_id, tid)
                        )
                    except Exception:
                        pass
                return tid

    return None


def _ensure_team_exists(cursor, statpal_team_id: Optional[int], team_name: str) -> Optional[int]:
    """
    Like _resolve_team_id but inserts the team if not found, so new teams from
    the schedule are automatically added to fantasy_ipl_teams.
    """
    if not team_name:
        return None
    existing = _resolve_team_id(cursor, statpal_team_id, team_name)
    if existing:
        return existing

    # Generate short_name from initials (e.g. "Mumbai Indians" -> "MI")
    words = team_name.split()
    short_name = ''.join(w[0].upper() for w in words if w)[:10]
    # Ensure uniqueness by appending team id suffix if needed
    if statpal_team_id:
        short_name = (short_name + str(statpal_team_id))[:10]

    try:
        cursor.execute(
            '''INSERT INTO fantasy_ipl_teams (team_name, statpal_team_id, short_name, full_name)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 statpal_team_id = COALESCE(statpal_team_id, VALUES(statpal_team_id)),
                 full_name = VALUES(full_name)''',
            (team_name, statpal_team_id, short_name, team_name)
        )
        if cursor.lastrowid:
            logger.info('_ensure_team_exists: inserted new team "%s" (statpal_id=%s)', team_name, statpal_team_id)
            return cursor.lastrowid
        # Row already existed (ON DUPLICATE KEY) — fetch it
        return _resolve_team_id(cursor, statpal_team_id, team_name)
    except Exception as e:
        logger.warning('_ensure_team_exists: failed to insert team "%s": %s', team_name, e)
        return None


# ============================================================================
# SEASON FIXTURE SYNC
# ============================================================================

def fetch_season_fixtures():
    """
    Fetch all fixtures for every active series (by statpal_tournament_id) and
    upsert them into fantasy_match_schedule.
    Runs 2x/day. API cost: 1 call per active series.
    """
    logger.info('fetch_season_fixtures: starting')

    conn_pre = get_db_connection()
    cur_pre = conn_pre.cursor(dictionary=True)
    try:
        cur_pre.execute(
            '''SELECT id, name, tournament_type, statpal_tournament_id
               FROM fantasy_series
               WHERE is_active = 1 AND statpal_tournament_id > 0
               ORDER BY id ASC'''
        )
        active_series = cur_pre.fetchall()
    finally:
        cur_pre.close()
        conn_pre.close()

    if not active_series:
        print('[fantasy] fetch_season_fixtures: no active series with a Statpal tournament ID — skipping')
        return

    print(f'[fantasy] fetch_season_fixtures: processing {len(active_series)} active series')
    for series in active_series:
        _fetch_tournament_matches(
            series['id'], series['name'],
            series['tournament_type'], series['statpal_tournament_id']
        )


def _fetch_tournament_matches(series_db_id: int, series_name: str, tournament_type: str, tournament_id: int):
    """Fetch all fixtures for one Statpal tournament and upsert into fantasy_match_schedule."""
    print(f'[fantasy] fetch_tournament_matches: fetching "{series_name}" (type={tournament_type}, id={tournament_id})')

    data = _statpal_get(f'cricket/season-schedule/{tournament_type}/{tournament_id}')
    if not data:
        print(f'[fantasy] fetch_tournament_matches: no data returned for tournament {tournament_id}')
        return

    category = (data.get('scores') or {}).get('category') or {}
    matches = category.get('match') or []
    if isinstance(matches, dict):
        matches = [matches]

    if not matches:
        print(f'[fantasy] fetch_tournament_matches: no matches returned for tournament {tournament_id}')
        return

    logger.info('fetch_tournament_matches: tournament "%s" has %d matches', series_name, len(matches))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        upsert_count = 0
        for m in matches:
            fixture_id_str = m.get('id')
            if not fixture_id_str:
                continue
            try:
                fixture_id = int(fixture_id_str)
            except (ValueError, TypeError):
                continue

            home = m.get('home') or {}
            away = m.get('away') or {}
            home_name = home.get('name', '')
            away_name = away.get('name', '')
            match_name = f'{home_name} vs {away_name}' if (home_name and away_name) else ''
            match_num = m.get('match_num', '')
            short_name = match_num or match_name

            date_str = m.get('date', '')   # "DD.MM.YYYY"
            time_str = m.get('time', '00:00')  # "HH:MM"
            match_date = None
            match_datetime_gmt = None
            if date_str:
                try:
                    dt = datetime.strptime(f'{date_str} {time_str}', '%d.%m.%Y %H:%M')
                    match_date = dt.date()
                    match_datetime_gmt = dt  # naive UTC
                except ValueError:
                    try:
                        match_date = datetime.strptime(date_str, '%d.%m.%Y').date()
                    except ValueError:
                        pass

            venue = m.get('venue') or None
            if not venue:
                # matchinfo block sometimes has venue in season-schedule
                matchinfo = m.get('matchinfo') or {}
                venue = matchinfo.get('venue') or matchinfo.get('ground') or None
            raw_status = m.get('status', '')
            status = _map_status(raw_status)

            try:
                home_api_id = int(home.get('id')) if home.get('id') else None
            except (ValueError, TypeError):
                home_api_id = None
            try:
                away_api_id = int(away.get('id')) if away.get('id') else None
            except (ValueError, TypeError):
                away_api_id = None

            team1_id = _ensure_team_exists(cursor, home_api_id, home_name)
            team2_id = _ensure_team_exists(cursor, away_api_id, away_name)

            result_comment = (m.get('comment') or {}).get('post') or None
            status_note = result_comment if (status == 'completed' and result_comment) else (match_num or raw_status)

            cursor.execute(
                '''INSERT INTO fantasy_match_schedule
                   (series_id, statpal_fixture_id, match_name, short_name,
                    team1_id, team2_id, match_date, match_datetime_gmt,
                    venue, match_type, status, status_note, last_synced_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                   ON DUPLICATE KEY UPDATE
                     match_name = VALUES(match_name),
                     short_name = VALUES(short_name),
                     team1_id = COALESCE(VALUES(team1_id), team1_id),
                     team2_id = COALESCE(VALUES(team2_id), team2_id),
                     match_date = VALUES(match_date),
                     match_datetime_gmt = VALUES(match_datetime_gmt),
                     venue = COALESCE(VALUES(venue), venue),
                     match_type = VALUES(match_type),
                     status = IF(status IN ('live', 'completed'), status, VALUES(status)),
                     status_note = COALESCE(VALUES(status_note), status_note),
                     last_synced_at = NOW()''',
                (series_db_id, fixture_id, match_name, short_name,
                 team1_id, team2_id, match_date, match_datetime_gmt,
                 venue, 't20', status, status_note)
            )
            upsert_count += 1

        conn.commit()
        print(f'[fantasy] fetch_tournament_matches: upserted {upsert_count} matches for "{series_name}"')
    except Exception as e:
        logger.error('fetch_tournament_matches DB error for series "%s": %s', series_name, e)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# SQUAD / LINEUP SYNC
# ============================================================================

def _map_role(role_str: str) -> str:
    """Map a Statpal player role string to our role ENUM (WK/BAT/AR/BOWL)."""
    r = (role_str or '').lower()
    if 'wicket' in r or 'keeper' in r:
        return 'WK'
    if 'all' in r:
        return 'AR'
    if 'bowl' in r:
        return 'BOWL'
    return 'BAT'


def fetch_tournament_squads(series_db_id: int = None, tournament_type: str = None, tournament_id: int = None):
    """
    Fetch squad (all players) for active series from Statpal.
    Upserts players into fantasy_ipl_players.
    If called without args, fetches squads for all active series.
    API cost: 1 call per active series.
    """
    if tournament_id is None:
        conn_pre = get_db_connection()
        cur_pre = conn_pre.cursor(dictionary=True)
        try:
            cur_pre.execute(
                'SELECT id, name, tournament_type, statpal_tournament_id FROM fantasy_series WHERE is_active = 1 AND statpal_tournament_id > 0'
            )
            active_series = cur_pre.fetchall()
        finally:
            cur_pre.close()
            conn_pre.close()

        for s in active_series:
            fetch_tournament_squads(s['id'], s['tournament_type'], s['statpal_tournament_id'])
        return

    print(f'[fantasy] fetch_tournament_squads: fetching squads for tournament {tournament_id} (type={tournament_type})')
    data = _statpal_get(f'cricket/squads/{tournament_type}/{tournament_id}')
    if not data:
        print(f'[fantasy] fetch_tournament_squads: no data for tournament {tournament_id}')
        return

    category = (data.get('squads') or {}).get('category') or {}
    teams = category.get('team') or []
    if isinstance(teams, dict):
        teams = [teams]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    players_added = 0
    try:
        for team in teams:
            team_name = team.get('name', '')
            try:
                team_api_id = int(team.get('id')) if team.get('id') else None
            except (ValueError, TypeError):
                team_api_id = None

            team_db_id = _resolve_team_id(cursor, team_api_id, team_name)
            if not team_db_id:
                print(f'[fantasy] fetch_tournament_squads: team not found: {team_name}')
                continue

            players = team.get('player') or []
            if isinstance(players, dict):
                players = [players]

            for player in players:
                # NOTE: Statpal squads have swapped fields:
                # player["id"]   = player display name (string)
                # player["name"] = numeric profileid (use as statpal_player_id)
                player_name = player.get('id', '')      # display name is in "id" field
                profileid_str = player.get('name', '')  # profileid is in "name" field

                if not profileid_str:
                    continue
                try:
                    statpal_player_id = int(profileid_str)
                except (ValueError, TypeError):
                    continue
                if not player_name:
                    continue

                role = _map_role(player.get('role', ''))

                cursor.execute(
                    '''INSERT INTO fantasy_ipl_players
                       (statpal_player_id, name, team_id, role)
                       VALUES (%s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                         name = VALUES(name),
                         team_id = VALUES(team_id),
                         updated_at = NOW()''',
                    (statpal_player_id, player_name, team_db_id, role)
                )
                players_added += 1

        conn.commit()
        print(f'[fantasy] fetch_tournament_squads: upserted {players_added} players for tournament {tournament_id}')
    except Exception as e:
        logger.error('fetch_tournament_squads error for tournament %d: %s', tournament_id, e)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def check_and_fetch_lineups():
    """
    Sync squads for active series from Statpal.
    Runs every 30 minutes. Costs 1 API call per active series.
    (Statpal provides tournament-level squads, not per-match lineups.)
    """
    fetch_tournament_squads()


# ============================================================================
# MATCH STATUS PROMOTION (no API call)
# ============================================================================

def promote_started_matches():
    """
    Promote matches from 'upcoming' to 'live' once their scheduled start time has passed.
    Runs every 5 minutes. No API calls — pure DB time comparison.
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


# ============================================================================
# LIVE SCORECARD SYNC
# ============================================================================

def _overs_to_balls(overs_str) -> int:
    """Convert '9.3' or '10' to balls. 9.3 overs = 9*6 + 3 = 57 balls."""
    try:
        s = str(overs_str or '0')
        if '.' in s:
            whole, partial = s.split('.', 1)
            return int(whole) * 6 + int(partial)
        return int(s) * 6
    except (ValueError, TypeError):
        return 0


def _parse_match_player_stats(match_data: dict) -> dict:
    """
    Extract per-player batting and bowling stats from a Statpal match object.
    Returns dict keyed by profileid (str) with aggregated stats.
    """
    innings = match_data.get('inning') or []
    if isinstance(innings, dict):
        innings = [innings]

    player_stats: dict = {}

    for inning in innings:
        # Batting
        bats_wrap = inning.get('batsmanstats') or {}
        batsmen = bats_wrap.get('player') or []
        if isinstance(batsmen, dict):
            batsmen = [batsmen]

        for b in batsmen:
            pid = b.get('profileid')
            if not pid:
                continue
            name = b.get('batsman', '')
            runs = int(b.get('r', 0) or 0)
            balls = int(b.get('b', 0) or 0)
            fours = int(b.get('s4', 0) or 0)
            sixes = int(b.get('s6', 0) or 0)
            dismissal_type = (b.get('dismissal_type') or '').lower()
            is_dismissed = dismissal_type not in ('not out', '', 'not started')

            if pid not in player_stats:
                player_stats[pid] = _empty_stats()
                player_stats[pid]['_name'] = name
            _merge_batting(player_stats[pid], {
                'runs_scored': runs,
                'balls_faced': balls,
                'fours': fours,
                'sixes': sixes,
                'is_dismissed': is_dismissed,
            })

        # Bowling
        bowls_wrap = inning.get('bowlers') or {}
        bowlers = bowls_wrap.get('player') or []
        if isinstance(bowlers, dict):
            bowlers = [bowlers]

        for bw in bowlers:
            pid = bw.get('profileid')
            if not pid:
                continue
            name = bw.get('bowler', '')
            balls_bowled = _overs_to_balls(bw.get('o', 0))
            runs_conceded = int(bw.get('r', 0) or 0)
            wickets = int(bw.get('w', 0) or 0)
            maidens = int(bw.get('m', 0) or 0)

            if pid not in player_stats:
                player_stats[pid] = _empty_stats()
                player_stats[pid]['_name'] = name
            _merge_bowling(player_stats[pid], {
                'wickets': wickets,
                'balls_bowled': balls_bowled,
                'runs_conceded': runs_conceded,
                'maidens': maidens,
            })

    return player_stats


def _find_match_in_livescores(data: dict, statpal_fixture_id: int) -> Optional[dict]:
    """Find a specific match in a Statpal livescores API response by fixture ID."""
    categories = (data.get('scores') or {}).get('category') or []
    if isinstance(categories, dict):
        categories = [categories]

    target_id = str(statpal_fixture_id)
    for cat in categories:
        match = cat.get('match')
        if not match:
            continue
        if isinstance(match, list):
            for m in match:
                if str(m.get('id', '')) == target_id:
                    return m
        elif isinstance(match, dict):
            if str(match.get('id', '')) == target_id:
                return match
    return None


def fetch_live_scorecard(statpal_fixture_id: int, db_match_id: int, match_data: dict = None):
    """
    Process batting/bowling scorecard for a live/completed fixture from Statpal.
    If match_data is provided (pre-fetched from livescores), use it directly.
    Otherwise fetch from livescores endpoint and find the match.
    Updates fantasy_player_match_stats and recalculates leaderboard.
    """
    logger.info('fetch_live_scorecard: fixture %s', statpal_fixture_id)

    if match_data is None:
        data = _statpal_get('cricket/livescores')
        if not data:
            return
        match_data = _find_match_in_livescores(data, statpal_fixture_id)
        if not match_data:
            print(f'[fantasy] fetch_live_scorecard: fixture {statpal_fixture_id} not found in livescores')
            return

    import re as _re

    raw_status = match_data.get('status', '')
    new_status = _map_status(raw_status)

    home_score = (match_data.get('home') or {}).get('totalscore', '')
    away_score = (match_data.get('away') or {}).get('totalscore', '')

    result_comment = (match_data.get('comment') or {}).get('post') or None

    # Build rich per-innings data for live scorecard display
    innings_raw = match_data.get('inning') or []
    if isinstance(innings_raw, dict):
        innings_raw = [innings_raw]
    innings_data = []
    for inn in innings_raw:
        total = inn.get('total') or {}
        tot_str = (total.get('tot', '') or '').strip()
        runs = 0
        overs = ''
        m_tot = _re.match(r'(\d+)\s*\(\s*([\d.]+)\s*\)', tot_str)
        if m_tot:
            runs = int(m_tot.group(1))
            overs = m_tot.group(2)
        else:
            # totalscore may be plain runs only (e.g. "180") — extract just the number
            m_plain = _re.match(r'^(\d+)', tot_str)
            if m_plain:
                runs = int(m_plain.group(1))
            # Try to derive overs from the sum of balls bowled by all bowlers
            bowls_fallback = (inn.get('bowlers') or {}).get('player') or []
            if isinstance(bowls_fallback, dict):
                bowls_fallback = [bowls_fallback]
            total_balls = sum(_overs_to_balls(bw.get('o', 0)) for bw in bowls_fallback)
            if total_balls:
                whole, rem = divmod(total_balls, 6)
                overs = f'{whole}.{rem}' if rem else str(whole)
        wickets = int(total.get('wickets', 0) or 0)
        rr = (total.get('rr', '') or '').strip()

        # Currently batting players (bat == "True")
        bats = (inn.get('batsmanstats') or {}).get('player') or []
        if isinstance(bats, dict):
            bats = [bats]
        batsmen = [
            {
                'name': b.get('batsman', ''),
                'runs': int(b.get('r', 0) or 0),
                'balls': int(b.get('b', 0) or 0),
                'sr': b.get('sr', ''),
            }
            for b in bats if str(b.get('bat', '')).lower() == 'true'
        ]

        # Currently bowling player (ball == "True")
        bowls = (inn.get('bowlers') or {}).get('player') or []
        if isinstance(bowls, dict):
            bowls = [bowls]
        bowler = next(
            (
                {
                    'name': bw.get('bowler', ''),
                    'overs': str(bw.get('o', '') or ''),
                    'wickets': int(bw.get('w', 0) or 0),
                    'runs': int(bw.get('r', 0) or 0),
                }
                for bw in bowls if str(bw.get('ball', '')).lower() == 'true'
            ),
            None,
        )

        innings_data.append({
            'num': int(inn.get('inningnum', 0) or 0),
            'name': inn.get('name', ''),
            'team': 'home' if inn.get('team', '') == 'localteam' else 'away',
            'runs': runs,
            'wickets': wickets,
            'overs': overs,
            'run_rate': rr,
            'batsmen': batsmen,
            'bowler': bowler,
        })

    live_score_json = json.dumps({
        'home': home_score,
        'away': away_score,
        'innings': innings_data,
    })

    player_stats = _parse_match_player_stats(match_data)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        for pid_str, stats in player_stats.items():
            try:
                statpal_pid = int(pid_str)
            except (ValueError, TypeError):
                continue

            cursor.execute(
                'SELECT id FROM fantasy_ipl_players WHERE statpal_player_id = %s', (statpal_pid,)
            )
            pr = cursor.fetchone()
            if not pr:
                player_name = stats.get('_name', '')
                if not player_name:
                    continue
                cursor.execute(
                    'INSERT IGNORE INTO fantasy_ipl_players (statpal_player_id, name, role) VALUES (%s, %s, %s)',
                    (statpal_pid, player_name, 'BAT')
                )
                conn.commit()
                cursor.execute(
                    'SELECT id FROM fantasy_ipl_players WHERE statpal_player_id = %s', (statpal_pid,)
                )
                pr = cursor.fetchone()
                if not pr:
                    continue
            player_db_id = pr['id']

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

        venue = match_data.get('venue') or None

        cursor.execute(
            '''UPDATE fantasy_match_schedule
               SET status = IF(%s IN ('live', 'completed', 'abandoned'), %s, status),
                   live_score = %s,
                   venue = COALESCE(%s, venue),
                   status_note = COALESCE(%s, status_note),
                   last_synced_at = NOW(),
                   scorecard_fetched = IF(%s = 'completed', 1, scorecard_fetched)
               WHERE id = %s''',
            (new_status, new_status, live_score_json, venue, result_comment, new_status, db_match_id)
        )
        conn.commit()

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
    """Fetch livescores once and update all currently live matches. Runs every 2 min."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, statpal_fixture_id FROM fantasy_match_schedule WHERE status = 'live'"
        )
        live = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if not live:
        return

    # Fetch livescores once and share across all live matches
    data = _statpal_get('cricket/livescores')
    if not data:
        print('[fantasy] update_live_matches: livescores fetch returned no data')
        return

    for row in live:
        try:
            match_data = _find_match_in_livescores(data, row['statpal_fixture_id'])
            if match_data:
                fetch_live_scorecard(row['statpal_fixture_id'], row['id'], match_data)
            else:
                print(f'[fantasy] update_live_matches: fixture {row["statpal_fixture_id"]} not in livescores (may have ended)')
        except Exception as e:
            logger.error('update_live_matches error for fixture %s: %s',
                         row['statpal_fixture_id'], e)


# ============================================================================
# LEADERBOARD RECALCULATION
# ============================================================================

def recalculate_match_leaderboard(match_id: int, conn=None):
    """Recompute fantasy_match_leaderboard for all users who have a team in this match."""
    close_conn = conn is None
    if conn is None:
        conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            'SELECT id, user_id FROM fantasy_user_selections WHERE match_id = %s',
            (match_id,)
        )
        selections = cursor.fetchall()

        cursor.execute(
            'SELECT player_id, fantasy_points FROM fantasy_player_match_stats WHERE match_id = %s',
            (match_id,)
        )
        stats_rows = cursor.fetchall()
        base_points = {r['player_id']: float(r['fantasy_points']) for r in stats_rows}

        leaderboard_data = []

        for sel in selections:
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
        logger.info('recalculate_match_leaderboard: done for match_id=%d, %d users',
                    match_id, len(leaderboard_data))
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

    _scheduler.add_job(
        fetch_season_fixtures,
        trigger='cron',
        hour='0,12',
        minute=5,
        id='series_sync',
        replace_existing=True,
        misfire_grace_time=300,
    )

    _scheduler.add_job(
        check_and_fetch_lineups,
        trigger='interval',
        minutes=30,
        id='squad_sync',
        replace_existing=True,
        misfire_grace_time=120,
    )

    _scheduler.add_job(
        promote_started_matches,
        trigger='interval',
        minutes=5,
        id='status_transition',
        replace_existing=True,
        misfire_grace_time=60,
    )

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
    threading.Thread(target=_initial_sync, daemon=True).start()


def _initial_sync():
    """Run once on startup to populate fixture schedule without waiting for cron."""
    try:
        print('[fantasy] _initial_sync: fetching season fixtures and squads on startup...')
        fetch_season_fixtures()
        fetch_tournament_squads()
        print('[fantasy] _initial_sync: done.')
    except Exception as e:
        print(f'[fantasy] _initial_sync error: {e}')
        logger.error('_initial_sync error: %s', e)


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info('Fantasy scheduler stopped.')
