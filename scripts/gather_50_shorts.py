import json
import time
import urllib.request
from playwright.sync_api import sync_playwright

def get_oembed(url):
    try:
        vid_id = url.split("/shorts/")[-1].split("?")[0]
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=VIDEO_ID&format=json".replace("VIDEO_ID", vid_id)
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("title", ""), data.get("author_name", "")
    except Exception as e:
        return "", ""

targets = [
    ("Alex Hormozi", "https://www.youtube.com/@AlexHormozi/shorts", 12),
    ("Tharun Speaks", "https://www.youtube.com/@TharunSpeaks/shorts", 12),
    ("Ali Abdaal", "https://www.youtube.com/@aliabdaal/shorts", 10),
    ("Dan Koe", "https://www.youtube.com/@DanKoeTalks/shorts", 8),
    ("Iman Gadzhi", "https://www.youtube.com/results?search_query=iman+gadzhi+shorts&sp=CAISAhAB", 8)
]

all_shorts = []
seen_urls = set()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    page = context.new_page()

    for creator, target_url, limit in targets:
        print(f"Scraping {creator} from {target_url}...")
        try:
            page.goto(target_url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            for _ in range(3):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(1500)

            hrefs = page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a[href*="/shorts/"]'));
                return links.map(a => a.getAttribute('href')).filter(h => h && h.length > 10);
            }''')

            count = 0
            for h in hrefs:
                if count >= limit:
                    break
                clean_id = h.split('/shorts/')[-1].split('?')[0]
                if not clean_id or len(clean_id) < 5:
                    continue
                full_url = f"https://www.youtube.com/shorts/{clean_id}"
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                title, author = get_oembed(full_url)
                if not title:
                    title = f"{creator} Short #{count+1}"

                all_shorts.append({
                    "id": clean_id,
                    "creator": author if author else creator,
                    "target_creator": creator,
                    "title": title,
                    "url": full_url
                })
                count += 1
                print(f"  [{count}/{limit}] {title} -> {full_url}")
        except Exception as e:
            print(f"Error {creator}: {e}")

    browser.close()

print(f"Total collected: {len(all_shorts)}")
with open("data/curated_50_shorts.json", "w", encoding="utf-8") as f:
    json.dump(all_shorts, f, indent=2)
print("Saved to data/curated_50_shorts.json")
