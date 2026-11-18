"""Inspect YouTube Shorts for Ishan Sharma and Tharun Speaks."""

import urllib.request
import re
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

def analyze_channel(handle, creator_name):
    url = f'https://www.youtube.com/{handle}/shorts'
    req = urllib.request.Request(url, headers=headers)
    print(f"\n=======================================================")
    print(f"ANALYZING CREATOR: {creator_name} ({handle})")
    print(f"=======================================================")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8')
            
            # Extract initial data JSON
            match = re.search(r'var ytInitialData = ({.*?});</script>', html)
            if not match:
                match = re.search(r'window\["ytInitialData"\] = ({.*?});</script>', html)
                
            shorts = []
            if match:
                try:
                    data = json.loads(match.group(1))
                    # Drill into tab contents
                    tabs = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
                    for tab in tabs:
                        tab_content = tab.get('tabRenderer', {}).get('content', {})
                        section_list = tab_content.get('sectionListRenderer', {}).get('contents', [])
                        for sec in section_list:
                            item_section = sec.get('itemSectionRenderer', {}).get('contents', [])
                            for is_item in item_section:
                                grid = is_item.get('gridRenderer', {}).get('items', [])
                                if not grid:
                                    grid = is_item.get('richGridRenderer', {}).get('contents', [])
                                for g_item in grid:
                                    r_item = g_item.get('richItemRenderer', {}).get('content', {})
                                    reel = r_item.get('reelItemRenderer', {})
                                    if reel:
                                        vid_id = reel.get('videoId')
                                        title = reel.get('headline', {}).get('simpleText', '')
                                        views = reel.get('viewCountText', {}).get('simpleText', '')
                                        if vid_id:
                                            shorts.append({'id': vid_id, 'title': title, 'views': views})
                except Exception as ex:
                    print(f"JSON parse error: {ex}")
            
            if not shorts:
                # Fallback to regex
                ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
                seen = set()
                for vid in ids:
                    if vid not in seen:
                        seen.add(vid)
                        shorts.append({'id': vid, 'title': 'Untitled Short', 'views': 'N/A'})
            
            print(f"Found {len(shorts)} shorts.")
            for i, s in enumerate(shorts[:8], 1):
                print(f"  {i}. https://www.youtube.com/shorts/{s['id']} | {s['title']} ({s['views']})")
                
            return shorts[:8]
    except Exception as e:
        print(f"Failed to fetch {handle}: {e}")
        return []

if __name__ == '__main__':
    ishan_shorts = analyze_channel('@IshanSharma7390', 'Ishan Sharma')
    tharun_shorts = analyze_channel('@TharunSpeaks', 'Tharun Speaks')
