import json
import urllib.request
from playwright.sync_api import sync_playwright

with open('data/curated_50_shorts.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

seen = {x['url'] for x in items}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://www.youtube.com/@LukeBelmar/shorts', timeout=25000)
    page.wait_for_timeout(3500)
    links = page.evaluate('() => Array.from(document.querySelectorAll("a[href*=\'/shorts/\']")).map(a => a.getAttribute("href"))')
    
    for h in links:
        if len(items) >= 50:
            break
        if not h:
            continue
        clean = h.split('/shorts/')[-1].split('?')[0]
        if not clean or len(clean) < 5:
            continue
        url = f'https://www.youtube.com/shorts/{clean}'
        if url in seen:
            continue
        seen.add(url)

        title, author = '', 'Luke Belmar'
        try:
            oembed_url = f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={clean}&format=json'
            req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                title = data.get('title', '')
                author = data.get('author_name', 'Luke Belmar')
        except Exception:
            pass

        items.append({
            'id': clean,
            'creator': author if author else 'Luke Belmar',
            'target_creator': 'Luke Belmar',
            'title': title if title else f'Luke Belmar Mindset Short #{len(items)+1}',
            'url': url
        })
        print(f"Added: {title or clean} -> {url}")

    browser.close()

print(f'Total now: {len(items)}')
with open('data/curated_50_shorts.json', 'w', encoding='utf-8') as f:
    json.dump(items, f, indent=2)
