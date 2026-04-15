"""
Backfill player image URLs from the CricketData fantasy squad API.

Fetches the squad for every match that has squad_fetched=1 and updates
image_url on fantasy_ipl_players for players where it is currently NULL.

Respects the existing API safety limit and adds a 1s delay between calls.

Usage:
    python server/backfill_player_images.py
"""

import os
import sys
import time

# Allow running from repo root or server/
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

import requests
import mysql.connector

CRICAPI_BASE = 'https://api.cricapi.com/v1'
DEFAULT_PLAYER_IMGS = {
    'https://cdorgapi.b-cdn.net/img/icon512.png',
    'https://h.cricapi.com/img/icon512.png',
}


def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=int(os.getenv('DB_PORT', 3306)),
    )


def fetch_squad(cricapi_match_id: str, api_key: str):
    resp = requests.get(
        f'{CRICAPI_BASE}/match_squad',
        params={'apikey': api_key, 'id': cricapi_match_id, 'offset': 0},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get('status') != 'success':
        print(f'  Non-success response: {data.get("status")} — {data.get("reason", "")}')
        return None, data.get('info', {})
    return data.get('data', []), data.get('info', {})


def main():
    api_key = os.getenv('CRICKETDATA_API_KEY')
    if not api_key:
        print('ERROR: CRICKETDATA_API_KEY not set in environment / .env')
        sys.exit(1)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch all matches that already have a squad synced
    cursor.execute(
        'SELECT id, cricapi_match_id, match_name FROM fantasy_match_schedule WHERE squad_fetched = 1 ORDER BY id'
    )
    matches = cursor.fetchall()
    print(f'Found {len(matches)} match(es) with squad_fetched=1\n')

    total_updated = 0
    hits_today = None

    for i, match in enumerate(matches):
        print(f'[{i+1}/{len(matches)}] {match["match_name"]} (cricapi_id={match["cricapi_match_id"]})')

        teams_data, api_info = fetch_squad(match['cricapi_match_id'], api_key)
        hits_today = api_info.get('hitsToday', hits_today)
        hits_limit = api_info.get('hitsLimit')

        if hits_today is not None and hits_limit is not None:
            print(f'  API usage: {hits_today}/{hits_limit}')
            if hits_today >= 9500:
                print('  WARNING: Approaching API daily limit — stopping to preserve budget.')
                break

        if teams_data is None:
            print('  Skipping (no data returned)')
            if i < len(matches) - 1:
                time.sleep(1)
            continue

        match_updated = 0
        for team_entry in teams_data:
            for p in team_entry.get('players', []):
                pid = p.get('id')
                if not pid:
                    continue
                raw_img = p.get('playerImg') or None
                image_url = None if (not raw_img or raw_img in DEFAULT_PLAYER_IMGS) else raw_img

                if image_url:
                    cursor.execute(
                        '''UPDATE fantasy_ipl_players
                           SET image_url = %s, updated_at = NOW()
                           WHERE cricapi_player_id = %s AND (image_url IS NULL OR image_url = '')''',
                        (image_url, pid),
                    )
                    if cursor.rowcount > 0:
                        match_updated += cursor.rowcount

        conn.commit()
        print(f'  Updated {match_updated} player image(s)')
        total_updated += match_updated

        # Respect API limits — 1 second between calls
        if i < len(matches) - 1:
            time.sleep(1)

    cursor.close()
    conn.close()
    print(f'\nDone! Total players updated: {total_updated}')


if __name__ == '__main__':
    main()
