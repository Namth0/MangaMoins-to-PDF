from unittest.mock import MagicMock

import pytest
import requests

from mangamoins_scraper.scraper import MangaMoinsScraper, ScraperError


class TestExtractSlug:
    def test_plain_slug(self):
        assert MangaMoinsScraper.extract_slug("OP1188") == "OP1188"

    def test_full_url(self):
        assert MangaMoinsScraper.extract_slug("https://mangamoins.com/scan/OP1188") == "OP1188"

    def test_full_url_with_trailing_slash(self):
        assert MangaMoinsScraper.extract_slug("https://mangamoins.com/scan/OP1188/") == "OP1188"

    def test_strips_whitespace(self):
        assert MangaMoinsScraper.extract_slug("  OP1188  ") == "OP1188"

    def test_unrecognized_url_raises(self):
        with pytest.raises(ScraperError):
            MangaMoinsScraper.extract_slug("https://mangamoins.com/other/OP1188")

    def test_url_missing_slug_raises(self):
        with pytest.raises(ScraperError):
            MangaMoinsScraper.extract_slug("https://mangamoins.com/scan")


class TestUrlExists:
    def test_returns_true_on_200(self):
        scraper = MangaMoinsScraper()
        scraper.session.head = MagicMock(return_value=MagicMock(status_code=200))
        assert scraper._url_exists("http://x/01.webp", "http://referer") is True

    def test_returns_false_on_404(self):
        scraper = MangaMoinsScraper()
        scraper.session.head = MagicMock(return_value=MagicMock(status_code=404))
        assert scraper._url_exists("http://x/01.webp", "http://referer") is False

    def test_falls_back_to_get_on_405(self):
        scraper = MangaMoinsScraper()
        scraper.session.head = MagicMock(return_value=MagicMock(status_code=405))
        get_resp = MagicMock(status_code=200)
        scraper.session.get = MagicMock(return_value=get_resp)
        assert scraper._url_exists("http://x/01.webp", "http://referer") is True
        scraper.session.get.assert_called_once()
        get_resp.close.assert_called_once()

    def test_returns_false_on_request_exception(self):
        scraper = MangaMoinsScraper()
        scraper.session.head = MagicMock(side_effect=requests.RequestException("boom"))
        assert scraper._url_exists("http://x/01.webp", "http://referer") is False


class TestDetectExtension:
    def test_returns_first_matching_extension(self):
        scraper = MangaMoinsScraper()
        scraper._url_exists = lambda url, referer: url.endswith(".png")
        assert scraper._detect_extension("http://x/base", "http://referer") == ".png"

    def test_returns_none_when_no_extension_matches(self):
        scraper = MangaMoinsScraper()
        scraper._url_exists = lambda url, referer: False
        assert scraper._detect_extension("http://x/base", "http://referer") is None


def _page_number(url: str) -> int:
    return int(url.rsplit("/", 1)[-1].split(".", 1)[0])


class TestProbePageCount:
    def test_hint_valid_extends_forward(self):
        scraper = MangaMoinsScraper()
        existing = {1, 2, 3, 4, 5}
        scraper._url_exists = lambda url, referer: _page_number(url) in existing
        count = scraper._probe_page_count("http://x/base", ".webp", "http://referer", hint=3)
        assert count == 5

    def test_hint_too_high_scans_backward(self):
        scraper = MangaMoinsScraper()
        existing = {1, 2, 3}
        scraper._url_exists = lambda url, referer: _page_number(url) in existing
        count = scraper._probe_page_count("http://x/base", ".webp", "http://referer", hint=10)
        assert count == 3

    def test_hint_exact_match(self):
        scraper = MangaMoinsScraper()
        existing = {1, 2, 3}
        scraper._url_exists = lambda url, referer: _page_number(url) in existing
        count = scraper._probe_page_count("http://x/base", ".webp", "http://referer", hint=3)
        assert count == 3

    def test_no_hint_scans_sequentially(self):
        scraper = MangaMoinsScraper()
        existing = {1, 2, 3, 4}
        scraper._url_exists = lambda url, referer: _page_number(url) in existing
        count = scraper._probe_page_count("http://x/base", ".webp", "http://referer", hint=0)
        assert count == 4

    def test_no_pages_found_returns_zero(self):
        scraper = MangaMoinsScraper()
        scraper._url_exists = lambda url, referer: False
        count = scraper._probe_page_count("http://x/base", ".webp", "http://referer", hint=0)
        assert count == 0

    def test_tolerates_single_missing_page_mid_scan(self):
        # No hint: sequential scan stops after two consecutive misses, so a
        # single missing page (e.g. transient CDN hiccup) shouldn't cut the
        # count short.
        scraper = MangaMoinsScraper()
        existing = {1, 2, 4, 5}
        scraper._url_exists = lambda url, referer: _page_number(url) in existing
        count = scraper._probe_page_count("http://x/base", ".webp", "http://referer", hint=0)
        assert count == 5


class TestFetchApiPageInfo:
    def test_extracts_base_and_hint(self):
        scraper = MangaMoinsScraper()
        scraper._fetch_api_json = lambda slug, referer: {
            "pagesBaseUrl": "http://x/abc123/",
            "pageNumbers": 12,
        }
        base, hint = scraper._fetch_api_page_info("OP1188", "http://referer")
        assert base == "http://x/abc123"
        assert hint == 12

    def test_raises_when_base_missing(self):
        scraper = MangaMoinsScraper()
        scraper._fetch_api_json = lambda slug, referer: {"pageNumbers": 12}
        with pytest.raises(ScraperError):
            scraper._fetch_api_page_info("OP1188", "http://referer")
