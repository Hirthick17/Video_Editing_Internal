import json
import time
from playwright.sync_api import sync_playwright

channels = [
    {"name": "Alex Hormozi", "url": "https://www.youtube.com/@AlexHormozi/shorts", "style": "Hormozi Kinetic / High Contrast / Direct Hook"},
    {"name": "Tharun Speaks", "url": "https://www.youtube.com/@TharunSpeaks/shorts", "style": "Aesthetic Edutainment / Paper Texture / Lo-Fi"},
    {"name": "Ali Abdaal", "url": "https://www.youtube.com/@aliabdaal/shorts", "style": "Clean Productivity / High Trust / Notion Aesthetic"},
    {"name": "Dan Koe", "url": "https://www.youtube.com/@DanKoeTalks/shorts", "style": "Dark Minimalist / Philosophical / Ambient Pacing"},
    {"name": "Iman Gadzhi", "url": "https://www.youtube.com/@ImanGadzhi/shorts", "style": "Cinematic Documentary / 3D Graphics / Film Grain"}
]

results = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    page = context.new_page()

    for ch in channels:
        print(f"Scraping {ch['name']}...")
        try:
            page.goto(ch["url"], timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            # Scroll down slightly to trigger loading
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(2000)

            # Extract links
            items = page.evaluate('''() => {
                const data = [];
                const links = document.querySelectorAll('a[href*="/shorts/"]');
                const seen = new Set();
                for (const a of links) {
                    const href = a.getAttribute('href');
                    if (href && href.includes('/shorts/') && !seen.has(href)) {
                        seen.add(href);
                        const titleEl = a.querySelector('#video-title') || a.querySelector('span[role="text"]') || a;
                        const title = a.getAttribute('title') || titleEl.innerText || a.innerText || '';
                        data.push({
                            href: href,
                            title: title.trim().replace(/\\n/g, ' ')
                        });
                    }
                }
                return data;
            }''')

            print(f"  Found {len(items)} items for {ch['name']}")
            for item in items[:12]:
                url = item['href']
                if not url.startswith('http'):
                    url = 'https://www.youtube.com' + url
                results.append({
                    "creator": ch["name"],
                    "style": ch["style"],
                    "title": item["title"],
                    "url": url
                })
        except Exception as e:
            print(f"  Error scraping {ch['name']}: {e}")

    browser.close()

print(f"Total collected: {len(results)}")
with open("data/scraped_shorts.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
print("Saved to data/scraped_shorts.json")
