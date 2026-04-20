import asyncio, csv, re, os
from datetime import datetime
from playwright.async_api import async_playwright

ITEMS = [
    ("Eggs",           "კვერცხი"),
    ("Bread",          "პური"),
    ("Rice",           "ბრინჯი"),
    ("Sunflower Oil",  "მზესუმზირის ზეთი"),
    ("Butter",         "კარაქი"),
    ("Sugar",          "შაქარი"),
    ("Flour",          "ფქვილი"),
]

STORES = [
    ("Carrefour",  "https://carrefour.ge/search?query={q}"),
    ("Goodwill",   "https://www.goodwill.ge/search/{q}"),
    ("Smart",      "https://smart.ge/ka/search?q={q}"),
    ("Nikora",     "https://nikora.ge/search?q={q}"),
    ("Ori Nabiji", "https://2nabiji.ge/en/search?query={q}"),
    ("Spar",       "https://sparonline.ge/search?q={q}"),
]

CARD = [".product-card",".product-item",".product",
        "[class*='product-card']","[class*='ProductCard']",
        "[class*='product_card']","li.item","article"]
NAME = [".product-name",".product-title","[class*='product-name']",
        "[class*='title']","h3","h2","h4"]
PRICE= ["[class*='price']","[class*='Price']",".cost",".amount"]

async def get_text(el, sels):
    for s in sels:
        try:
            found = await el.query_selector(s)
            if found:
                t = (await found.inner_text()).strip()
                if t: return t
        except: pass
    return None

async def scrape(page, store_name, url_tpl, item_name, item_q):
    rows = []
    url = url_tpl.replace("{q}", item_q)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(4000)
        for cs in CARD:
            cards = await page.query_selector_all(cs)
            if not cards: continue
            for card in cards[:5]:
                name = await get_text(card, NAME)
                price_raw = await get_text(card, PRICE)
                if name and price_raw:
                    nums = re.findall(r'\d+[.,]?\d*', price_raw)
                    if nums:
                        price = float(nums[0].replace(',','.'))
                        rows.append([datetime.now().strftime("%Y-%m-%d"),
                                     store_name, item_name, name[:80], price])
            if rows: break
        if not rows:
            os.makedirs("debug", exist_ok=True)
            await page.screenshot(path=f"debug/{store_name}_{item_name}.png", full_page=False)
            print(f"  No data — screenshot saved for {store_name}/{item_name}")
    except Exception as e:
        print(f"  ERROR {store_name}/{item_name}: {e}")
    return rows

async def main():
    all_rows = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0 Safari/537.36"
        )
        page = await ctx.new_page()
        for store_name, url_tpl in STORES:
            print(f"\n=== {store_name} ===")
            for item_name, item_q in ITEMS:
                print(f"  {item_name}...")
                rows = await scrape(page, store_name, url_tpl, item_name, item_q)
                all_rows.extend(rows)
                await asyncio.sleep(2)
        await browser.close()

    with open("prices.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date","Store","Category","Product","Price (GEL)"])
        w.writerows(all_rows)

    print(f"\nFinished. {len(all_rows)} prices saved to prices.csv")

asyncio.run(main())
