import re, urllib.parse, requests
from bs4 import BeautifulSoup
from typing import Optional, Tuple

HDRS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}
SIZE_RE = re.compile(r"(/books/\d+)([sml])(/[^/?#]+\.(?:jpe?g|png|webp))", re.I)

def _size_variant(url: str, size: str) -> str:
    m = SIZE_RE.search(url)
    if not m or size.lower() not in {"s","m","l"}:
        return url
    prefix = url[: m.start(1)]
    books_part, _, tail = m.groups()
    return f"{prefix}{books_part}{size.lower()}{tail}"

def _fetch_img(url: str) -> Optional[bytes]:
    r = requests.get(url, headers=HDRS, timeout=20)
    return r.content if r.ok and r.headers.get("content-type","").startswith("image/") else None

def fetch_goodreads_cover_by_title(title: str, size: str = "l") -> Optional[Tuple[str, bytes]]:
    """Return (cover_url_used, image_bytes) for the top Goodreads result of a title."""
    # 1) Search
    q = urllib.parse.urlencode({"q": title.strip()})
    search_url = f"https://www.goodreads.com/search?{q}"
    sr = requests.get(search_url, headers=HDRS, timeout=20)
    if sr.status_code != 200:
        return None

    soup = BeautifulSoup(sr.text, "html.parser")
    row = soup.select_one("table.tableList tr")
    if not row:
        return None
    href = (row.select_one("a.bookTitle") or {}).get("href")
    if not href:
        return None
    book_url = urllib.parse.urljoin("https://www.goodreads.com", href)

    # 2) Book page → og:image
    br = requests.get(book_url, headers=HDRS, timeout=25)
    if br.status_code != 200:
        return None
    bs = BeautifulSoup(br.text, "html.parser")
    og = bs.find("meta", attrs={"property": "og:image"})
    img_url = og.get("content") if og else None

    # Fallback to legacy image if needed
    if not img_url:
        img = bs.select_one("#coverImage")
        if img and img.get("src"):
            img_url = img["src"]

    if not img_url or "nophoto/book" in img_url:
        return None
    img_url = urllib.parse.urljoin("https://www.goodreads.com", img_url)

    # 3) Try requested size; fall back to original
    try_url = _size_variant(img_url, size)
    img_bytes = _fetch_img(try_url) or _fetch_img(img_url)
    if not img_bytes:
        return None
    return (try_url if img_bytes else img_url, img_bytes)

# --- Example ---
used_url, bytes_ = fetch_goodreads_cover_by_title("Romeo and Juliet", size="l")
if bytes_:
    open("gatsby.jpg", "wb").write(bytes_)
    print("Saved:", used_url)
