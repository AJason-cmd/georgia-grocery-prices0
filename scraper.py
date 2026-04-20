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
    ("Sugar",         "\u10e8\u10d0\u10e5\u10d0\u10e0\u10d
