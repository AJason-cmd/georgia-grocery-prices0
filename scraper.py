import asyncio
import csv
import re
import os
from datetime import datetime
from playwright.async_api import async_playwright

ITEMS = [
    ("Eggs", "kvercxi"),
    ("Bread", "puri"),
    ("Rice", "brinji"),
    ("Sunflower Oil", "mzesumziris zeti"),
    ("Butter", "karaki"),
    ("Sugar", "shakari"),
    ("Flour", "pkvili"),
]

STORES = [
    ("Carrefour", "https://carrefour.ge/search?query={q}"),
    ("Goodwill", "https://www.goodwill.ge/search/{q}"),
    ("Smart", "https://smart.ge/ka/search?q={q}"),
    ("Nikora", "https://nikora.ge/search?q={q}"),
    ("Ori Nabiji", "https://2nabiji.ge/en/search?query={q}"),
    ("Spar", "https://sparonline.ge/search?q={q}"),
]


async def scrape(page, store_name, url_tpl, item_name, item_q):
    rows = []
    url = url_tpl.replace("{q}", item_q)
    os.makedirs("debug", exist_ok=True)

    try:
        print(f"  Visiting: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        await page.screenshot(path=f"debug/{store_name}_{item_name}.png", full_page=False)

        page_text = await page.inner_text("body")
        lines = [l.strip() for l in page_text.splitlines() if l.strip()]

        prices_found = []
        i = 0
        while i < len(lines):
            line = lines[i]
            price_match = re.search(r'(\d+[.,]\d+|\d+)\s*$', line)
            if price_match:
                price_val = float(price_match.group(1).replace(',', '.'))
                if 0.5 <= price_val <= 150:
                    product_name = lines[i - 1] if i > 0 else "Unknown"
                    if len(product_name) > 3 and not re.match(r'^\d+$', product_name):
                        prices_found.append((product_name[:80], price_val))
            i += 1

        for product_name, price_val in prices_found[:5]:
            rows.append([
                datetime.now().strftime("%Y-%m-%d"),
                store_name,
                item_name,
                product_name,
                price_val
            ])

        if rows:
            print(f"  OK - {len(rows)} prices found")
        else:
            print(f"  No prices found - check debug screenshot")

    except Exception as e:
        print(f"  ERROR {store_name}/{item_name}: {e}")
