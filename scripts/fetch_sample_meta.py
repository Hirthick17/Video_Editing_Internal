"""Fetch detailed metadata for Ishan Sharma and Tharun Speaks shorts."""

import urllib.request
import json
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

ishan_ids = [
    "-zL-hXIYRFQ", "SN1pPQg-5PU", "5HPfF6mCq2I", "5bFS4wIl4W0",
    "vX7FK2h56J4", "mzwYz2Zd7RA", "g_hADQCgv2g", "G0gZHkT-DCg"
]

tharun_ids = [
    "F-OMZ6xuKSg", "UCSYvoB5JLI", "5f3CcNk4jTQ", "UJH0dBzI_Ic",
    "lpOxAmgthvU", "O-IqsUT9bm0", "RjMYOeY8wGw", "PvHgYa6It3Q"
]

def fetch_oembed(video_id):
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return {
                'id': video_id,
                'title': data.get('title', 'Unknown Title'),
                'author': data.get('author_name', 'Unknown Author'),
                'url': f"https://www.youtube.com/shorts/{video_id}",
                'thumbnail': data.get('thumbnail_url', '')
            }
    except Exception as e:
        return {'id': video_id, 'title': f'Error: {e}', 'url': f"https://www.youtube.com/shorts/{video_id}"}

print("=== ISHAN SHARMA SHORTS METADATA ===")
ishan_meta = []
for vid in ishan_ids:
    meta = fetch_oembed(vid)
    ishan_meta.append(meta)
    print(f"[{meta['id']}] {meta['title']}")
    time.sleep(0.3)

print("\n=== THARUN SPEAKS SHORTS METADATA ===")
tharun_meta = []
for vid in tharun_ids:
    meta = fetch_oembed(vid)
    tharun_meta.append(meta)
    print(f"[{meta['id']}] {meta['title']}")
    time.sleep(0.3)

with open('reports/creator_shorts_sample.json', 'w', encoding='utf-8') as f:
    json.dump({'ishan_sharma': ishan_meta, 'tharun_speaks': tharun_meta}, f, indent=2)
print("\nSaved to reports/creator_shorts_sample.json")
