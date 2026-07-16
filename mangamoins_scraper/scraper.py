"""Core scraping logic for MangaMoins chapters.

MangaMoins deliberately poisons the `pagesBaseUrl` field returned by its
internal JSON API (extra random prefix/suffix wrapped around the real
folder id) as a basic anti-scraping measure. The `pageNumbers` count,
however, is accurate. So the strategy below decouples "where are the
images" (base URL) from "how many pages" (count):

1. Warm up a session (cookies) by visiting the homepage.
2. Call the internal JSON API (/api/v1/scan?slug=...) to get a page count
   hint and a base URL candidate, then validate the candidate by probing
   page 01 with a real HTTP request.
3. If the API's base URL is invalid, fall back to parsing the reader HTML
   page directly (works only if the page is server-rendered).
4. If that also fails, fall back to driving a real headless browser
   (Playwright) to read the actual rendered <img> URL, which is not
   obfuscated.
5. Once a valid base URL + extension is known, the exact page count is
   confirmed/adjusted by probing around the count hint (or, lacking a
   hint, by scanning from page 1 until pages stop existing).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

BASE_URL = "https://mangamoins.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

CANDIDATE_EXTENSIONS = (".webp", ".png", ".jpg", ".jpeg")
MAX_PROBE_PAGES = 400

logger = logging.getLogger(__name__)


class ScraperError(RuntimeError):
    """Raised when no strategy managed to find chapter pages."""


@dataclass
class ChapterPages:
    slug: str
    referer: str
    image_urls: list[str]
    source: str  # "api" | "html" | "playwright"


class MangaMoinsScraper:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            }
        )

    @staticmethod
    def extract_slug(target: str) -> str:
        """Extract a chapter slug (e.g. OP1188) from a URL or return as-is."""
        target = target.strip()
        if target.startswith("http://") or target.startswith("https://"):
            path = urlparse(target).path.strip("/")
            parts = path.split("/")
            if len(parts) >= 2 and parts[0] == "scan":
                return parts[1]
            raise ScraperError(f"URL non reconnue (attendu /scan/<slug>) : {target}")
        return target

    def warm_up_session(self) -> None:
        """Visit the homepage first to obtain any session cookies."""
        resp = self.session.get(f"{BASE_URL}/", timeout=30)
        resp.raise_for_status()

    # -- low level helpers -------------------------------------------------

    def _url_exists(self, url: str, referer: str) -> bool:
        headers = {"Referer": referer}
        try:
            resp = self.session.head(url, headers=headers, timeout=15, allow_redirects=True)
            if resp.status_code == 405:  # some CDNs don't support HEAD
                resp = self.session.get(url, headers=headers, timeout=15, stream=True)
                resp.close()
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def _detect_extension(self, base: str, referer: str) -> str | None:
        for ext in CANDIDATE_EXTENSIONS:
            if self._url_exists(f"{base}/01{ext}", referer):
                return ext
        return None

    def _probe_page_count(self, base: str, ext: str, referer: str, hint: int = 0) -> int:
        def exists(n: int) -> bool:
            return self._url_exists(f"{base}/{n:02d}{ext}", referer)

        if hint > 0 and exists(hint):
            n = hint
            while n < MAX_PROBE_PAGES and exists(n + 1):
                n += 1
            return n

        if hint > 0:
            n = hint
            while n > 1 and not exists(n):
                n -= 1
            if exists(n):
                return n

        # No usable hint: scan sequentially until two consecutive misses.
        last_found = 0
        consecutive_missing = 0
        page = 1
        while page <= MAX_PROBE_PAGES and consecutive_missing < 2:
            if exists(page):
                last_found = page
                consecutive_missing = 0
            else:
                consecutive_missing += 1
            page += 1
        return last_found

    # -- resolution strategies ----------------------------------------------

    def _fetch_api_json(self, slug: str, referer: str) -> dict:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": referer,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        resp = self.session.get(
            f"{BASE_URL}/api/v1/scan",
            params={"slug": slug},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if str(data.get("status", "")).lower() == "error":
            raise ScraperError(data.get("message", "Erreur API MangaMoins"))
        return data

    def _fetch_api_page_info(self, slug: str, referer: str) -> tuple[str, int]:
        """Return (base_url_candidate, page_count_hint) from the API.

        The base URL may be intentionally invalid (anti-scraping); the
        page count is generally accurate and reused even if the base is
        rejected by validation.
        """
        data = self._fetch_api_json(slug, referer)
        base = str(data.get("pagesBaseUrl", "")).rstrip("/")
        count_hint = int(data.get("pageNumbers", 0) or 0)
        if not base:
            raise ScraperError("pagesBaseUrl manquant dans la réponse API")
        return base, count_hint

    def _resolve_base_from_html(self, slug: str, referer: str) -> tuple[str, str, int]:
        """Fallback: parse the reader HTML page directly (server-rendered only)."""
        resp = self.session.get(referer, headers={"Referer": f"{BASE_URL}/"}, timeout=30)
        resp.raise_for_status()
        html = resp.text

        total_match = re.search(r'id=["\']readerTotalPages["\'][^>]*>(\d+)<', html)
        count_hint = int(total_match.group(1)) if total_match else 0

        img_match = re.search(
            r'(?:src|data-src)=["\']([^"\']+\.(?:webp|png|jpe?g))["\']',
            html,
            re.IGNORECASE,
        )
        if not img_match:
            raise ScraperError("Impossible d'extraire une image depuis le HTML du lecteur")

        first_url = img_match.group(1)
        if not first_url.startswith("http"):
            first_url = f"{BASE_URL}{first_url}"

        m = re.match(r"^(https?://.+)/(\d+)(\.[a-zA-Z0-9]+)(?:\?.*)?$", first_url)
        if not m:
            raise ScraperError(f"Format d'URL d'image inattendu : {first_url}")

        return m.group(1), m.group(3), count_hint

    def _resolve_base_from_playwright(self, slug: str, referer: str) -> tuple[str, str]:
        """Fallback: use a real headless browser to read the rendered image URL.

        Necessary for MangaMoins because pages are rendered client-side
        (SPA) and the API's base URL is deliberately obfuscated.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ScraperError(
                "Playwright n'est pas installé. "
                "Installez-le avec: pip install -r requirements-optional.txt "
                "&& playwright install chromium"
            ) from exc

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=USER_AGENT)
                page.goto(referer, wait_until="networkidle")
                src = page.eval_on_selector(
                    "img.reader-manga-page, #readerContent img, main img",
                    "el => el.src",
                )
            finally:
                browser.close()

        if not src:
            raise ScraperError("Impossible d'extraire l'image depuis le navigateur")

        m = re.match(r"^(https?://.+)/(\d+)(\.[a-zA-Z0-9]+)(?:\?.*)?$", src)
        if not m:
            raise ScraperError(f"Format d'URL d'image inattendu : {src}")

        return m.group(1), m.group(3)

    # -- public API ----------------------------------------------------------

    def get_chapter_pages(self, target: str, force_playwright: bool = False) -> ChapterPages:
        slug = self.extract_slug(target)
        referer = f"{BASE_URL}/scan/{slug}"

        base: str | None = None
        ext: str | None = None
        count_hint = 0
        source = "playwright"

        if not force_playwright:
            self.warm_up_session()

            try:
                api_base, api_count_hint = self._fetch_api_page_info(slug, referer)
                count_hint = api_count_hint
                detected_ext = self._detect_extension(api_base, referer)
                if detected_ext:
                    base, ext, source = api_base, detected_ext, "api"
                else:
                    logger.info(
                        "Base URL renvoyée par l'API invalide (anti-scraping), "
                        "recherche de la vraie base via HTML/navigateur..."
                    )
            except Exception as exc:  # noqa: BLE001 - deliberately broad, we fall back
                logger.info("API échouée (%s)", exc)

            if base is None:
                try:
                    html_base, html_ext, html_count_hint = self._resolve_base_from_html(
                        slug, referer
                    )
                    base, ext, source = html_base, html_ext, "html"
                    count_hint = count_hint or html_count_hint
                except Exception as exc:  # noqa: BLE001
                    logger.info("Fallback HTML échoué (%s), tentative via Playwright...", exc)

        if base is None or ext is None:
            base, ext = self._resolve_base_from_playwright(slug, referer)
            source = "playwright"

        count = self._probe_page_count(base, ext, referer, hint=count_hint)
        if count <= 0:
            raise ScraperError("Aucune page trouvée pour ce chapitre")

        urls = [f"{base}/{i:02d}{ext}" for i in range(1, count + 1)]
        return ChapterPages(slug=slug, referer=referer, image_urls=urls, source=source)

    def download_image(self, url: str, referer: str) -> bytes:
        resp = self.session.get(url, headers={"Referer": referer}, timeout=60)
        resp.raise_for_status()
        return resp.content
