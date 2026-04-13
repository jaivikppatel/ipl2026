"""
Fantasy Cricket Points Calculation Engine
Dream11-style scoring rules for IPL T20 matches.

All functions are pure (no DB access) for easy unit testing and reuse.
"""


def calculate_player_points(stats: dict) -> float:
    """
    Calculate fantasy points for a single player based on their match stats.

    Args:
        stats: dict with keys:
            did_bat, runs_scored, balls_faced, fours, sixes, is_dismissed, is_duck
            did_bowl, balls_bowled, runs_conceded, wickets, maidens
            catches, stumpings, run_outs_direct, run_outs_indirect

    Returns:
        float fantasy points (can be negative due to economy/SR penalties)
    """
    points = 0.0

    # -------------------------------------------------------------------------
    # BATTING
    # -------------------------------------------------------------------------
    if stats.get('did_bat'):
        runs = stats.get('runs_scored', 0)
        balls = stats.get('balls_faced', 0)
        fours = stats.get('fours', 0)
        sixes = stats.get('sixes', 0)
        dismissed = stats.get('is_dismissed', False)
        duck = stats.get('is_duck', False)

        # Base run points
        points += runs * 0.5

        # Boundary bonuses
        points += fours * 1
        points += sixes * 2

        # Milestone bonuses
        if runs >= 100:
            points += 16
        elif runs >= 50:
            points += 8
        elif runs >= 30:
            points += 4

        # Duck penalty (dismissed for 0, only if actually batted and dismissed)
        if duck and dismissed:
            points -= 2

        # Strike rate modifier (minimum 10 balls faced, only if dismissed or match over)
        if balls >= 10:
            sr = (runs / balls) * 100
            if sr > 170:
                points += 6
            elif sr >= 150:
                points += 4
            elif sr >= 130:
                points += 2
            elif sr < 50:
                points -= 6
            elif sr < 70:
                points -= 4
            elif sr < 100:
                points -= 2

    # -------------------------------------------------------------------------
    # BOWLING
    # -------------------------------------------------------------------------
    if stats.get('did_bowl'):
        wickets = stats.get('wickets', 0)
        balls_bowled = stats.get('balls_bowled', 0)
        runs_conceded = stats.get('runs_conceded', 0)
        maidens = stats.get('maidens', 0)

        # Per-wicket points
        points += wickets * 25

        # Wicket haul bonuses
        if wickets >= 5:
            points += 16
        elif wickets >= 4:
            points += 8
        elif wickets >= 3:
            points += 4

        # Maiden over bonus
        points += maidens * 12

        # Economy rate modifier (minimum 2 overs = 12 balls)
        if balls_bowled >= 12:
            overs = balls_bowled / 6
            economy = runs_conceded / overs
            if economy <= 5:
                points += 6
            elif economy <= 6:
                points += 4
            elif economy <= 7:
                points += 2
            elif economy >= 12:
                points -= 6
            elif economy >= 11:
                points -= 4
            elif economy >= 10:
                points -= 2

    # -------------------------------------------------------------------------
    # FIELDING
    # -------------------------------------------------------------------------
    points += stats.get('catches', 0) * 8
    points += stats.get('stumpings', 0) * 12
    points += stats.get('run_outs_direct', 0) * 12
    points += stats.get('run_outs_indirect', 0) * 6

    return round(points, 2)


def apply_captain_vc_multipliers(team_players: list, base_points: dict) -> float:
    """
    Apply Captain (2x) and Vice-Captain (1.5x) multipliers and return total team points.

    Args:
        team_players: list of dicts with keys: player_id, is_captain, is_vice_captain
        base_points: dict mapping player_id -> fantasy_points (without multiplier)

    Returns:
        float total fantasy points for the team
    """
    total = 0.0
    for tp in team_players:
        pid = tp['player_id']
        pts = float(base_points.get(pid, 0))
        if tp.get('is_captain'):
            pts *= 2.0
        elif tp.get('is_vice_captain'):
            pts *= 1.5
        total += pts
    return round(total, 2)


def parse_scorecard_batting(batting_entry: dict) -> dict:
    """
    Parse a batting entry from the CricketData match_scorecard API response
    into our stats dict format.

    Expected batting_entry keys from API:
        batsman (name), r (runs), b (balls), 4s, 6s, sr (strike rate),
        dismissal-text or similar
    """
    runs = int(batting_entry.get('r', 0) or 0)
    balls = int(batting_entry.get('b', 0) or 0)
    fours = int(batting_entry.get('4s', 0) or 0)
    sixes = int(batting_entry.get('6s', 0) or 0)
    dismissal = batting_entry.get('wicket-code', '') or batting_entry.get('dismissal-text', '')
    dismissed = bool(dismissal and dismissal.lower() not in ('', 'not out', 'dnb', 'absent'))

    return {
        'did_bat': True,
        'runs_scored': runs,
        'balls_faced': balls,
        'fours': fours,
        'sixes': sixes,
        'is_dismissed': dismissed,
        'is_duck': (runs == 0 and dismissed),
    }


def parse_scorecard_bowling(bowling_entry: dict) -> dict:
    """
    Parse a bowling entry from the CricketData match_scorecard API response
    into our stats dict format.

    Expected bowling_entry keys from API:
        bowler (name), o (overs), m (maidens), r (runs), w (wickets),
        wd (wides), nb (no-balls)
    """
    overs_str = str(bowling_entry.get('o', '0') or '0')
    # Overs may be "3.4" (3 overs 4 balls) — convert to total balls
    try:
        parts = overs_str.split('.')
        full_overs = int(parts[0])
        extra_balls = int(parts[1]) if len(parts) > 1 else 0
        balls_bowled = full_overs * 6 + extra_balls
    except (ValueError, IndexError):
        balls_bowled = 0

    maidens = int(bowling_entry.get('m', 0) or 0)
    runs_conceded = int(bowling_entry.get('r', 0) or 0)
    wickets = int(bowling_entry.get('w', 0) or 0)

    return {
        'did_bowl': True,
        'balls_bowled': balls_bowled,
        'runs_conceded': runs_conceded,
        'wickets': wickets,
        'maidens': maidens,
    }
