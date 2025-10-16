import re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

def _first_sel(el, sels: list[str]):
    for s in sels:
        x = el.select_one(s)
        if x:
            return x
    return None

def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _abs(base: str, href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(base, href)

def scrape_category(url: str, selectors: dict) -> List[Dict]:
    seen_pages = set()
    to_visit = [url]
    items: List[Dict] = []

    while to_visit:
        page = to_visit.pop(0)
        if page in seen_pages:
            continue
        seen_pages.add(page)

        r = requests.get(page, timeout=25, headers={"User-Agent": UA})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        cards = []
        for card_sel in selectors["card"]:
            cards = soup.select(card_sel)
            if cards:
                break

        for c in cards:
            title_el = _first_sel(c, selectors["title"])
            price_el = _first_sel(c, selectors["price"])
            if not title_el or not price_el:
                continue
            title = _clean_text(title_el.get_text())
            price = _clean_text(price_el.get_text())
            href = title_el.get("href")
            items.append({
                "title": title,
                "price": price,
                "url": _abs(page, href) if selectors.get("link_from_title", True) else None
            })

        # простая пагинация
        for a in soup.select("a"):
            txt = (a.get_text() or "").strip().lower()
            if re.fullmatch(r"[0-9]{1,3}", txt) or "след" in txt or "next" in txt:
                nxt = _abs(page, a.get("href"))
                if nxt and urlparse(nxt).netloc == urlparse(page).netloc and nxt not in seen_pages:
                    to_visit.append(nxt)

    return items

def scrape_products_multi(urls: List[str], selectors: dict) -> List[Dict]:
    out: List[Dict] = []
    for u in urls:
        out.extend(scrape_category(u, selectors))
    return out
