"""
Backfill player image blob data from existing image_url values.

For every player in fantasy_ipl_players that has an image_url set but
is missing image_data (or whose image_data_url differs from image_url),
this script fetches the image over HTTP, base64-encodes it into a data URI,
and stores it in image_data + image_data_url.

This mirrors how user profile pictures are stored in the users table.

Usage (from repo root):
    python server/backfill_player_image_data.py

Run once after migration 016 has been applied. Safe to re-run — only
processes players whose blob is missing or stale.
"""

import base64
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

import requests
import mysql.connector

# Known placeholder images that shouldn't be stored as blobs
PLACEHOLDER_URLS = {
    'https://cdorgapi.b-cdn.net/img/icon512.png',
    'https://h.cricapi.com/img/icon512.png',
}

# Fallback MIME type map based on URL extension
EXT_MIME = {
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png':  'image/png',
    '.webp': 'image/webp',
    '.gif':  'image/gif',
}


def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=int(os.getenv('DB_PORT', 3306)),
    )


def detect_mime(url: str, content_type: str | None) -> str:
    """Detect MIME type from Content-Type header, falling back to URL extension."""
    if content_type:
        mime = content_type.split(';')[0].strip().lower()
        if mime.startswith('image/'):
            return mime
    # Fallback: check URL extension
    lower_url = url.lower().split('?')[0]
    for ext, mime in EXT_MIME.items():
        if lower_url.endswith(ext):
            return mime
    return 'image/jpeg'  # last resort


def fetch_image_data_uri(url: str) -> str | None:
    """Fetch image from URL and return as base64 data URI, or None on failure."""
    try:
        resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        resp.raise_for_status()
        mime = detect_mime(url, resp.headers.get('Content-Type'))
        b64 = base64.b64encode(resp.content).decode('ascii')
        return f'data:{mime};base64,{b64}'
    except Exception as e:
        print(f'    WARN: Failed to fetch {url}: {e}')
        return None


def main():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Find all players that need blob data
    cursor.execute(
        '''SELECT id, name, image_url
           FROM fantasy_ipl_players
           WHERE image_url IS NOT NULL
             AND image_url != ''
             AND (image_data IS NULL
                  OR image_data = ''
                  OR image_data_url IS NULL
                  OR image_data_url != image_url)
           ORDER BY id'''
    )
    players = cursor.fetchall()
    print(f'Found {len(players)} player(s) needing blob data backfill\n')

    updated = 0
    skipped = 0
    failed = 0

    for i, player in enumerate(players):
        url = player['image_url']
        print(f'[{i+1}/{len(players)}] {player["name"]} (id={player["id"]}) — {url}')

        if url in PLACEHOLDER_URLS:
            print('    SKIP: placeholder URL')
            skipped += 1
            continue

        data_uri = fetch_image_data_uri(url)
        if data_uri is None:
            failed += 1
            time.sleep(0.1)
            continue

        cursor.execute(
            '''UPDATE fantasy_ipl_players
               SET image_data = %s, image_data_url = %s, updated_at = NOW()
               WHERE id = %s''',
            (data_uri, url, player['id']),
        )
        conn.commit()
        print(f'    OK ({len(data_uri)} chars)')
        updated += 1
        time.sleep(0.1)  # Be polite to CDN

    cursor.close()
    conn.close()

    print(f'\nDone. Updated={updated}, Skipped={skipped}, Failed={failed}')


if __name__ == '__main__':
    main()
