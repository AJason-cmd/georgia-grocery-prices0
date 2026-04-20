import asyncio
import csv
import re
import os
from datetime import datetime
from playwright.async_api import async_playwright

ITEMS = [
    ("Eggs",          "\u10d9\u10d5\u10d4\u10e0\u10ea\u10ee\u10d8"),
    ("Bread",         "\u10de\u10e3\u10e0\u10d8"),
    ("Rice",          "\u10d1\u10e0\u10d8\u10dc\u10ef\u10d8"),
    ("Sunflower Oil", "\u10db\u10d6\u10d4\u10e1\u10e3\u10db\u10d6\u10d8\u10e0\u10d8\u10e1 \u10d6\u10d4\u10d7\u10d8"),
    ("Butter",        "\u10d9\u10d0\u10e0\u10d0\u10e5\u10d8"),
    ("Sugar",         "\u10e8\u10d0\u10e5\u10d0\u10e0\u10d8"),
    ("Flour",         "\u10e4\u10e5\u10d5\u10d8\u10da\u10d8"),
]

STORES = [
    ("Carrefour",  "https://carrefour.ge/search?query={q}"),
    ("Goodwill",   "https://www.goodwill.ge/search/{q}"),
    ("Smart",      "https://smart.ge/ka/search?q={q}"),
    ("Nikora",     "https://nikora.ge/search?q={q}"),
    ("Ori Nabiji", "https://2nabiji.ge/en/search?query={q}"),
    ("Spar",       "https://sparonline.ge/search?q={q}"),
]

CARD_SELS = [
    ".product-card", ".product-item", ".product",
    "[class*='product-card']", "[class*='ProductCard']",
    "[class*='product_card']", "[class*='product-item']",
    "li.item", "article", ".item-box", ".catalog-item",
    "[class*='catalog']", "[class*='item']",
]

NAME_SELS = [
    "[class*='product-name']", "[class*='product-title']",
    "[class*='title']", "[class*='name']",
    "h1", "h2", "h3", "h4", "p.name", "span.name",
]

PRICE_SELS = [
    "[class*='price']", "[class*='Price']",
    "[class*='cost']", "[class*='amount']",
    "span.price", "div.price", "p.price",
    "[class*='sale']", "[class*='Sale']",
]

async def get_text(el, sels):
    for s in sels:
        try:
            found = await el.query_selector(s)
            if found:
                t = (await found.inner_text()).strip()
                if t:
                    return t
        except:
            pass
    return None

async def scrape(page, store_name, url_tpl, item_name, item_q):
    rows = []
    url = url_tpl.replace("{q}", item_q)
    os.makedirs("debug", exist_ok=True)

    try:
        print(f"  GET {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(7000)
        await page.screenshot(path=f"debug/{store_name}_{item_name}.png", full_page=False)

        # Try card-based scraping
        for cs in CARD_SELS:
            cards = await page.query_selector_all(cs)
            if not cards:
                continue
            print(f"  Found {len(cards)} cards with selector: {cs}")
            for card in cards[:5]:
                name = await get_text(card, NAME_SELS)
                price_raw = await get_text(card, PRICE_SELS)
                if name and price_raw:
                    nums = re.findall(r'\d+[.,]?\d*', price_raw)
                    if nums:
                        price = float(nums[0].replace(',', '.'))
                        if 0.3 <= price <= 200:
                            rows.append([
                                datetime.now().strftime("%Y-%m-%d"),
                                store_name, item_name,
                                name[:80], price
                            ])
            if rows:
                break

        # Fallback: scan all visible prices on the page
        if not rows:
            print(f"  Trying fallback text scan...")
            all_price_els = await page.query_selector_all(
                "[class*='price'],[class*='Price'],[class*='cost']"
            )
            for el in all_price_els[:10]:
                try:
                    text = (await el.inner_text()).strip()
                    nums = re.findall(r'\d+[.,]?\d*', text)
                    if nums:
                        price = float(nums[0].replace(',', '.'))
                        if 0.3 <= price <= 200:
                            rows.append([
                                datetime.now().strftime("%Y-%m-%d"),
                                store_name, item_name,
                                f"{item_name} at {store_name}", price
                            ])
                except:
                    pass

        print(f"  Result: {len(rows)} prices")

    except Exception as e:
        print(f"  ERROR: {e}")

    return rows


async def main():
    all_rows = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        for store_name, url_tpl in STORES:
            print(f"\n=== {store_name} ===")
            for item_name, item_q in ITEMS:
                print(f"  Searching: {item_name}")
                rows = await scrape(page, store_name, url_tpl, item_name, item_q)
                all_rows.extend(rows)
                await asyncio.sleep(3)

        await browser.close()

    with open("prices.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Store", "Category", "Product", "Price (GEL)"])
        w.writerows(all_rows)

    print(f"\nFinished. {len(all_rows)} prices saved.")


asyncio.run(main())
