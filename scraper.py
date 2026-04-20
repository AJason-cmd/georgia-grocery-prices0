import asyncio
import re
import os
import requests
from datetime import datetime
from playwright.async_api import async_playwright
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
from io import BytesIO

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
    ("Carrefour",  "https://carrefour.ge/search?query={q}",  "https://carrefour.ge"),
    ("Goodwill",   "https://www.goodwill.ge/search/{q}",     "https://www.goodwill.ge"),
    ("Smart",      "https://smart.ge/ka/search?q={q}",       "https://smart.ge"),
    ("Nikora",     "https://nikora.ge/search?q={q}",         "https://nikora.ge"),
    ("Ori Nabiji", "https://2nabiji.ge/en/search?query={q}", "https://2nabiji.ge"),
    ("Spar",       "https://sparonline.ge/search?q={q}",     "https://sparonline.ge"),
]

CARD_SELS = [
    ".product-card", ".product-item", ".product",
    "[class*='product-card']", "[class*='ProductCard']",
    "[class*='product_card']", "[class*='product-item']",
    "li.item", "article", ".item-box", ".catalog-item",
    "[class*='catalog-item']",
]

NAME_SELS  = ["[class*='product-name']","[class*='product-title']","[class*='title']","[class*='name']","h2","h3","h4"]
PRICE_SELS = ["[class*='price']","[class*='Price']","[class*='cost']","[class*='amount']","span.price","div.price"]
IMG_SELS   = ["img[class*='product']","img[class*='Product']","img","picture img"]
LINK_SELS  = ["a[class*='product']","a[class*='Product']","a[href*='/product']","a[href*='/item']","a"]


async def get_attr(el, sels, attr):
    for s in sels:
        try:
            found = await el.query_selector(s)
            if found:
                val = await found.get_attribute(attr)
                if val and len(val) > 3:
                    return val
        except:
            pass
    return None


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


async def scrape(page, store_name, url_tpl, base_url, item_name, item_q):
    rows = []
    url = url_tpl.replace("{q}", item_q)
    os.makedirs("debug", exist_ok=True)

    try:
        print(f"  GET {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(7000)
        await page.screenshot(path=f"debug/{store_name}_{item_name}.png", full_page=False)

        for cs in CARD_SELS:
            cards = await page.query_selector_all(cs)
            if not cards:
                continue
            print(f"  {len(cards)} cards found ({cs})")
            for card in cards[:5]:
                name      = await get_text(card, NAME_SELS)
                price_raw = await get_text(card, PRICE_SELS)
                img_src   = await get_attr(card, IMG_SELS, "src")
                link_href = await get_attr(card, LINK_SELS, "href")

                if not img_src:
                    img_src = await get_attr(card, IMG_SELS, "data-src")

                if name and price_raw:
                    nums = re.findall(r'\d+[.,]?\d*', price_raw)
                    if nums:
                        price = float(nums[0].replace(',', '.'))
                        if 0.3 <= price <= 200:
                            if link_href and not link_href.startswith("http"):
                                link_href = base_url + link_href
                            if img_src and not img_src.startswith("http"):
                                img_src = base_url + img_src
                            rows.append({
                                "date":     datetime.now().strftime("%Y-%m-%d"),
                                "store":    store_name,
                                "category": item_name,
                                "product":  name[:80],
                                "price":    price,
                                "image":    img_src or "",
                                "link":     link_href or url,
                            })
            if rows:
                break

        print(f"  Result: {len(rows)} prices")

    except Exception as e:
        print(f"  ERROR: {e}")

    return rows


def download_image(url):
    try:
        r = requests.get(url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"
        })
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            return BytesIO(r.content)
    except:
        pass
    return None


def build_excel(all_rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Prices"

    # --- Styles ---
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    center      = Alignment(horizontal="center", vertical="center", wrap_text=True)
    border_side = Side(style="thin", color="CCCCCC")
    thin_border = Border(left=border_side, right=border_side,
                         top=border_side,  bottom=border_side)

    # --- Headers ---
    headers = ["Image", "Date", "Store", "Category", "Product", "Price (GEL)", "Link"]
    col_widths = [18, 12, 14, 14, 40, 14, 50]

    for col, (h, w) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill      = header_fill
        cell.font      = header_font
        cell.alignment = center
        cell.border    = thin_border
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.row_dimensions[1].height = 20

    # --- Sort by category then price ---
    all_rows.sort(key=lambda r: (r["category"], r["price"]))

    # --- Data rows ---
    row_num = 2
    for r in all_rows:
        ws.row_dimensions[row_num].height = 65

        # Image column
        img_data = download_image(r["image"]) if r["image"] else None
        if img_data:
            try:
                img = XLImage(img_data)
                img.width  = 80
                img.height = 80
                img.anchor = f"A{row_num}"
                ws.add_image(img)
            except:
                ws.cell(row=row_num, column=1, value="(no image)")
        else:
            ws.cell(row=row_num, column=1, value="(no image)")

        # Data columns
        vals = [None, r["date"], r["store"], r["category"], r["product"], r["price"]]
        for col, val in enumerate(vals, start=1):
            if val is None:
                continue
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.alignment = center
            cell.border    = thin_border
            if col == 6:
                cell.font = Font(bold=True, color="1F4E79", size=11)

        # Link column as hyperlink
        link_cell = ws.cell(row=row_num, column=7, value="Open product page")
        link_cell.hyperlink  = r["link"]
        link_cell.font       = Font(color="0563C1", underline="single")
        link_cell.alignment  = center
        link_cell.border     = thin_border

        # Alternate row color
        if row_num % 2 == 0:
            fill = PatternFill("solid", fgColor="EBF3FB")
            for col in range(1, 8):
                ws.cell(row=row_num, column=col).fill = fill

        row_num += 1

    wb.save("prices.xlsx")
    print(f"Saved prices.xlsx with {len(all_rows)} rows")


async def main():
    all_rows = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()
        await page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )

        for store_name, url_tpl, base_url in STORES:
            print(f"\n=== {store_name} ===")
            for item_name, item_q in ITEMS:
                print(f"  {item_name}...")
                rows = await scrape(page, store_name, url_tpl, base_url, item_name, item_q)
                all_rows.extend(rows)
                await asyncio.sleep(3)

        await browser.close()

    if all_rows:
        build_excel(all_rows)
    else:
        print("No data collected - check debug screenshots in artifacts")


asyncio.run(main())
