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

eggs = "\u10d9\u10d5\u10d4\u10e0\u10ea\u10ee\u10d8"
bread = "\u10de\u10e3\u10e0\u10d8"
rice = "\u10d1\u10e0\u10d8\u10dc\u10ef\u10d8"
oil = "\u10db\u10d6\u10d4\u10e1\u10e3\u10db\u10d6\u10d8\u10e0\u10d8\u10e1 \u10d6\u10d4\u10d7\u10d8"
butter = "\u10d9\u10d0\u10e0\u10d0\u10e5\u10d8"
sugar = "\u10e8\u10d0\u10e5\u10d0\u10e0\u10d8"
flour = "\u10e4\u10e5\u10d5\u10d8\u10da\u10d8"

ITEMS = [
    ("Eggs", eggs),
    ("Bread", bread),
    ("Rice", rice),
    ("Sunflower Oil", oil),
    ("Butter", butter),
    ("Sugar", sugar),
    ("Flour", flour),
]

STORES = [
    ("Spar", "https://sparonline.ge/search?q={q}", "https://sparonline.ge"),
    ("Ori Nabiji", "https://2nabiji.ge/en/search?query={q}", "https://2nabiji.ge"),
]

NAME_SELS = [
    "[class*='product-name']","[class*='product-title']",
    "[class*='ProductName']","[class*='name']",
    "[class*='title']","h2","h3","h4",
]
PRICE_SELS = [
    "[class*='price']","[class*='Price']",
    "[class*='cost']","[class*='amount']",
    "span.price","div.price",
]
IMG_SELS = ["img[class*='product']","i
