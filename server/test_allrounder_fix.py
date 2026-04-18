"""
Simulation: All-rounder batting + bowling fix
=============================================
Tests the merge logic in fetch_live_scorecard WITHOUT touching any real DB.

Scenario: Hardik Pandya bats in inning 1, then bowls in inning 2.
The Statpal livescores API is polled every 2 minutes.

We simulate 3 API poll snapshots:
  Snapshot A: End of inning 1 — only batting data visible
  Snapshot B: Middle of inning 2 — only bowling data visible (old bug: batting wiped)
  Snapshot C: End of match — both innings in data (ideal)

For each snapshot we run _parse_match_player_stats() (the real parse function),
then apply OLD merge logic (overwrite) vs NEW merge logic (preserve) and show
what fantasy_points would have been stored.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fantasy_points import calculate_player_points

# ── Reuse the real parse + merge helpers (no DB imports needed) ───────────

def _overs_to_balls(overs_str) -> int:
    try:
        s = str(overs_str or '0')
        if '.' in s:
            whole, partial = s.split('.', 1)
            return int(whole) * 6 + int(partial)
        return int(s) * 6
    except (ValueError, TypeError):
        return 0


def _empty_stats() -> dict:
    return {
        'did_bat': False, 'runs_scored': 0, 'balls_faced': 0, 'fours': 0, 'sixes': 0,
        'is_dismissed': False, 'is_duck': False,
        'did_bowl': False, 'wickets': 0, 'balls_bowled': 0, 'runs_conceded': 0, 'maidens': 0,
        'catches': 0, 'stumpings': 0, 'run_outs_direct': 0, 'run_outs_indirect': 0,
    }


def _merge_batting(target, parsed):
    target['did_bat'] = True
    target['runs_scored'] += parsed.get('runs_scored', 0)
    target['balls_faced'] += parsed.get('balls_faced', 0)
    target['fours'] += parsed.get('fours', 0)
    target['sixes'] += parsed.get('sixes', 0)
    target['is_dismissed'] = parsed.get('is_dismissed', False)


def _merge_bowling(target, parsed):
    target['did_bowl'] = True
    target['wickets'] += parsed.get('wickets', 0)
    target['balls_bowled'] += parsed.get('balls_bowled', 0)
    target['runs_conceded'] += parsed.get('runs_conceded', 0)
    target['maidens'] += parsed.get('maidens', 0)


def _parse_match_player_stats(match_data: dict) -> dict:
    innings = match_data.get('inning') or []
    if isinstance(innings, dict):
        innings = [innings]

    player_stats: dict = {}

    for inning in innings:
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
                'runs_scored': runs, 'balls_faced': balls,
                'fours': fours, 'sixes': sixes, 'is_dismissed': is_dismissed,
            })

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
                'wickets': wickets, 'balls_bowled': balls_bowled,
                'runs_conceded': runs_conceded, 'maidens': maidens,
            })

    return player_stats


# ── NEW merge logic (the fix) ─────────────────────────────────────────────

def apply_new_merge(new_stats: dict, existing_db_row) -> dict:
    """
    Mirrors the fix we added to fetch_live_scorecard.
    existing_db_row is a dict like the DB row, or None if no prior row.
    Returns the final stats dict after merging.
    """
    stats = dict(new_stats)  # copy
    if existing_db_row:
        if not stats.get('did_bat') and existing_db_row.get('did_bat'):
            stats['did_bat'] = True
            stats['runs_scored'] = int(existing_db_row['runs_scored'])
            stats['balls_faced'] = int(existing_db_row['balls_faced'])
            stats['fours'] = int(existing_db_row['fours'])
            stats['sixes'] = int(existing_db_row['sixes'])
            stats['is_dismissed'] = bool(existing_db_row['is_dismissed'])
        if not stats.get('did_bowl') and existing_db_row.get('did_bowl'):
            stats['did_bowl'] = True
            stats['wickets'] = int(existing_db_row['wickets'])
            stats['balls_bowled'] = int(existing_db_row['balls_bowled'])
            stats['runs_conceded'] = int(existing_db_row['runs_conceded'])
            stats['maidens'] = int(existing_db_row['maidens'])
    stats['is_duck'] = (
        stats.get('runs_scored', 0) == 0 and
        stats.get('is_dismissed', False) and
        stats.get('did_bat', False)
    )
    return stats


# ── Mock Statpal livescores snapshots ─────────────────────────────────────
#
# Hardik Pandya (profileid "999") plays for CSK:
#   Inning 1 (CSK bats): 45 runs off 28 balls, 3 fours, 2 sixes — dismissed
#   Inning 2 (MI bats):  Hardik bowls 4 overs (24 balls), 2 wickets, 28 runs, 0 maidens
#
# NOTE: Statpal livescores sometimes returns ONLY the current inning.
# Snapshot A = end of inning 1 (only inning 1 visible)
# Snapshot B = during inning 2 (ONLY inning 2 visible — this is the bug trigger)
# Snapshot C = match complete (BOTH innings visible — ideal full data)

SNAPSHOT_A = {
    'inning': [
        {
            'inningnum': 1,
            'name': 'CSK',
            'batsmanstats': {
                'player': [
                    {
                        'profileid': '999',
                        'batsman': 'Hardik Pandya',
                        'r': '45', 'b': '28', 's4': '3', 's6': '2',
                        'dismissal_type': 'caught',
                    },
                    {
                        'profileid': '111',
                        'batsman': 'Ruturaj Gaikwad',
                        'r': '72', 'b': '48', 's4': '6', 's6': '4',
                        'dismissal_type': 'not out',
                    },
                ]
            },
            'bowlers': {'player': [
                {'profileid': '222', 'bowler': 'Jasprit Bumrah',
                 'o': '4', 'r': '22', 'w': '1', 'm': '0'},
            ]},
        }
    ]
}

SNAPSHOT_B = {
    # Only inning 2 is returned by the API (bug scenario)
    'inning': [
        {
            'inningnum': 2,
            'name': 'MI',
            'batsmanstats': {
                'player': [
                    {
                        'profileid': '333',
                        'batsman': 'Rohit Sharma',
                        'r': '35', 'b': '22', 's4': '4', 's6': '1',
                        'dismissal_type': 'caught',
                    },
                ]
            },
            'bowlers': {'player': [
                {
                    'profileid': '999',
                    'bowler': 'Hardik Pandya',
                    'o': '4', 'r': '28', 'w': '2', 'm': '0',
                },
                {'profileid': '444', 'bowler': 'Devon Conway',
                 'o': '2', 'r': '18', 'w': '0', 'm': '0'},
            ]},
        }
    ]
}

SNAPSHOT_C = {
    # Full match — both innings present
    'inning': [
        {
            'inningnum': 1,
            'name': 'CSK',
            'batsmanstats': {
                'player': [
                    {
                        'profileid': '999',
                        'batsman': 'Hardik Pandya',
                        'r': '45', 'b': '28', 's4': '3', 's6': '2',
                        'dismissal_type': 'caught',
                    },
                    {
                        'profileid': '111',
                        'batsman': 'Ruturaj Gaikwad',
                        'r': '72', 'b': '48', 's4': '6', 's6': '4',
                        'dismissal_type': 'not out',
                    },
                ]
            },
            'bowlers': {'player': [
                {'profileid': '222', 'bowler': 'Jasprit Bumrah',
                 'o': '4', 'r': '22', 'w': '1', 'm': '0'},
            ]},
        },
        {
            'inningnum': 2,
            'name': 'MI',
            'batsmanstats': {
                'player': [
                    {
                        'profileid': '333',
                        'batsman': 'Rohit Sharma',
                        'r': '35', 'b': '22', 's4': '4', 's6': '1',
                        'dismissal_type': 'caught',
                    },
                ]
            },
            'bowlers': {'player': [
                {
                    'profileid': '999',
                    'bowler': 'Hardik Pandya',
                    'o': '4', 'r': '28', 'w': '2', 'm': '0',
                },
                {'profileid': '444', 'bowler': 'Devon Conway',
                 'o': '2', 'r': '18', 'w': '0', 'm': '0'},
            ]},
        },
    ]
}


# ── Helpers ───────────────────────────────────────────────────────────────

def pts_breakdown(stats: dict) -> str:
    lines = []
    if stats.get('did_bat'):
        r = stats['runs_scored']
        b = stats['balls_faced']
        f = stats['fours']
        s = stats['sixes']
        lines.append(f"  Batting: {r} runs ({b}b, {f}×4, {s}×6), dismissed={stats['is_dismissed']}, duck={stats.get('is_duck', False)}")
    if stats.get('did_bowl'):
        w = stats['wickets']
        bb = stats['balls_bowled']
        rc = stats['runs_conceded']
        m = stats['maidens']
        overs = bb / 6
        econ = round(rc / overs, 2) if overs else 0
        lines.append(f"  Bowling: {w}w, {bb} balls ({bb//6}.{bb%6} ov), {rc} runs, {m} maidens, econ={econ}")
    return '\n'.join(lines) if lines else '  (no data)'


def run_step(label: str, snapshot: dict, existing_db_row):
    print(f"\n{'='*60}")
    print(f"STEP: {label}")
    print(f"{'='*60}")

    parsed = _parse_match_player_stats(snapshot)
    raw = parsed.get('999')

    print(f"\n[Parsed from API for Hardik Pandya (pid=999)]")
    if raw:
        print(pts_breakdown(raw))
    else:
        print("  (not in this snapshot)")
        raw = _empty_stats()
        raw['_name'] = 'Hardik Pandya'

    # OLD behaviour: no merge, just overwrite
    old_stats = dict(raw)
    old_stats['is_duck'] = (
        old_stats.get('runs_scored', 0) == 0 and
        old_stats.get('is_dismissed', False) and
        old_stats.get('did_bat', False)
    )
    old_pts = calculate_player_points(old_stats)

    # NEW behaviour: merge with existing DB row first
    new_stats = apply_new_merge(raw, existing_db_row)
    new_pts = calculate_player_points(new_stats)

    print(f"\n[OLD logic — overwrite with API data]")
    print(pts_breakdown(old_stats))
    print(f"  ➜ fantasy_points stored = {old_pts}")

    print(f"\n[NEW logic — merge with existing DB row]")
    print(pts_breakdown(new_stats))
    print(f"  ➜ fantasy_points stored = {new_pts}")

    if old_pts != new_pts:
        print(f"\n  ⚠ DIFFERENCE: old={old_pts}  new={new_pts}  (delta={round(new_pts-old_pts,2)})")
    else:
        print(f"\n  ✓ Same result (both = {new_pts})")

    # Return what NEW logic would write to DB (for next step's existing_db_row)
    return new_stats


# ── Expected points (manual calculation) ─────────────────────────────────
def expected_points():
    # Batting: 45 runs + 3 fours bonus + 2 sixes bonus + 30+ milestone + SR
    bat_runs = 45
    bat_pts = bat_runs * 1  # 45
    bat_pts += 3 * 1        # four bonus: 3
    bat_pts += 2 * 3        # six bonus: 6
    bat_pts += 4            # 30+ milestone: 4
    # SR = 45/28 * 100 = 160.7 → +4
    sr = (45 / 28) * 100
    bat_pts += 4            # SR 150-170: +4
    # Bowling: 2 wickets (50) + economy 28/4=7.0 (+2)
    bowl_pts = 2 * 25       # 50
    econ = 28 / 4           # 7.0 — exactly ≤7 → +2
    bowl_pts += 2
    total = bat_pts + bowl_pts
    return bat_pts, bowl_pts, total, sr


# ── Run simulation ────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("FANTASY POINTS ALL-ROUNDER FIX — SIMULATION")
    print("Player: Hardik Pandya (CSK·AR, profileid=999)")
    print("Match: CSK vs MI")

    bat_pts, bowl_pts, expected_total, sr = expected_points()
    print(f"\n[Expected correct points]")
    print(f"  Batting ({bat_pts:.1f}) + Bowling ({bowl_pts:.1f}) = {expected_total:.1f} pts")
    print(f"  (SR={sr:.1f})")

    # Step 1: End of inning 1 — no prior DB row
    db_row_after_A = run_step(
        "SNAPSHOT A — End of inning 1 (CSK bats, Hardik batted)",
        SNAPSHOT_A,
        existing_db_row=None,
    )

    # Step 2: During inning 2 — API only returns inning 2
    # existing DB row = what NEW logic stored after step 1
    db_row_after_B = run_step(
        "SNAPSHOT B — During inning 2 (MI bats, only inning 2 in API response)",
        SNAPSHOT_B,
        existing_db_row=db_row_after_A,
    )

    # Step 3: Full match data available
    db_row_after_C = run_step(
        "SNAPSHOT C — Match complete (both innings in API response)",
        SNAPSHOT_C,
        existing_db_row=db_row_after_B,
    )

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    final_new = calculate_player_points(apply_new_merge(
        _parse_match_player_stats(SNAPSHOT_B).get('999', _empty_stats()),
        db_row_after_A,
    ))
    snap_b_old = _parse_match_player_stats(SNAPSHOT_B).get('999', _empty_stats())
    snap_b_old['is_duck'] = False
    final_old = calculate_player_points(snap_b_old)

    print(f"\n  Expected correct total  : {expected_total:.1f}")
    print(f"  OLD code (snapshot B)   : {final_old:.1f}  ← Bug: batting wiped")
    print(f"  NEW code (snapshot B)   : {final_new:.1f}  ← Fix: batting preserved")
    print(f"  After snapshot C (both) : {calculate_player_points(db_row_after_C):.1f}")
    print()
