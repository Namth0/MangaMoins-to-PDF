from pathlib import Path

from mangamoins_scraper.gui import (
    default_download_directory,
    default_output_name,
    is_missing_browser_error,
)


class TestDefaultOutputName:
    def test_plain_slug(self):
        assert default_output_name("OP1188") == "OP1188.pdf"

    def test_full_url(self):
        assert default_output_name("https://mangamoins.com/scan/OP1188") == "OP1188.pdf"

    def test_empty_input(self):
        assert default_output_name("") == "chapitre.pdf"

    def test_whitespace_only_input(self):
        assert default_output_name("   ") == "chapitre.pdf"

    def test_unrecognized_url_falls_back_to_placeholder(self):
        assert default_output_name("https://mangamoins.com/other/OP1188") == "chapitre.pdf"


class TestIsMissingBrowserError:
    def test_matches_playwright_missing_executable_message(self):
        exc = RuntimeError(
            "Executable doesn't exist at C:\\Users\\x\\ms-playwright\\chromium-1234\\chrome.exe"
        )
        assert is_missing_browser_error(exc) is True

    def test_does_not_match_unrelated_error(self):
        assert is_missing_browser_error(RuntimeError("connection timed out")) is False


class TestDefaultDownloadDirectory:
    def test_returns_existing_directory(self):
        directory = default_download_directory()
        assert isinstance(directory, Path)
        assert directory.is_dir()
