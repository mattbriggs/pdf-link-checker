"""
Integration tests for the full pdf_link_checker pipeline.

These tests exercise the complete stack — PDF extraction, concurrent link
checking, and report writing — using real test PDFs from the ``data/``
directory. HTTP requests are mocked so tests run offline and deterministically.

Fixtures ``pdf_short`` and ``pdf_long`` are provided by ``tests/conftest.py``.
"""

import csv
import json
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from pdf_link_checker.checker import ConcurrentLinkChecker, RequestsLinkChecker
from pdf_link_checker.cli import run
from pdf_link_checker.extractor import PyPDFExtractor
from pdf_link_checker.models import LinkRecord
from pdf_link_checker.reporter import CSVReportWriter, JSONReportWriter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


# ---------------------------------------------------------------------------
# Extraction → Checking → CSV pipeline (short PDF)
# ---------------------------------------------------------------------------

class TestShortPDFPipeline:
    """Integration tests for the short test PDF (pdflink.pdf)."""

    def test_extract_then_check_then_write_csv(self, pdf_short, tmp_path):
        """Full pipeline with short PDF produces a valid CSV report."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)
        assert len(records) >= 1

        checker = RequestsLinkChecker()
        with patch.object(
            checker._session, "get", return_value=_make_mock_response(404)
        ):
            concurrent = ConcurrentLinkChecker(strategy=checker, max_workers=2)
            resolved = concurrent.check_all(records)

        out = tmp_path / "short_report.csv"
        CSVReportWriter().write(resolved, out)

        assert out.exists()
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        # Header + at least one data row
        assert len(rows) >= 2
        assert rows[0] == ["page", "uri", "status", "request-error"]

    def test_all_records_have_status_after_pipeline(self, pdf_short):
        """After checking, every record has a non-None status."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)

        checker = RequestsLinkChecker()
        with patch.object(
            checker._session, "get", return_value=_make_mock_response(200)
        ):
            concurrent = ConcurrentLinkChecker(strategy=checker)
            resolved = concurrent.check_all(records)

        for r in resolved:
            assert r.status is not None

    def test_records_sorted_by_page_after_pipeline(self, pdf_short):
        """Resolved records are sorted by page number."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)

        checker = RequestsLinkChecker()
        with patch.object(
            checker._session, "get", return_value=_make_mock_response(200)
        ):
            concurrent = ConcurrentLinkChecker(strategy=checker)
            resolved = concurrent.check_all(records)

        pages = [r.page for r in resolved]
        assert pages == sorted(pages)

    def test_known_adobe_uri_extracted(self, pdf_short):
        """The known Adobe URI is extracted from pdflink.pdf."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)
        uris = [r.uri.strip().lower() for r in records]
        assert any("adobe" in u for u in uris)


# ---------------------------------------------------------------------------
# Extraction → Checking → JSON pipeline (long PDF)
# ---------------------------------------------------------------------------

class TestLongPDFPipeline:
    """Integration tests for the long test PDF (testpdf.pdf)."""

    def test_extract_then_check_then_write_json(self, pdf_long, tmp_path):
        """Full pipeline with long PDF produces a valid JSON report."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_long)
        assert len(records) >= 1

        checker = RequestsLinkChecker()
        with patch.object(
            checker._session, "get", return_value=_make_mock_response(200)
        ):
            concurrent = ConcurrentLinkChecker(strategy=checker, max_workers=4)
            resolved = concurrent.check_all(records)

        out = tmp_path / "long_report.json"
        JSONReportWriter().write(resolved, out)

        assert out.exists()
        with open(out, encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == len(resolved)

    def test_known_wikipedia_uri_extracted(self, pdf_long):
        """The known Wikipedia URI is extracted from testpdf.pdf."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_long)
        uris = [r.uri.strip() for r in records]
        assert any("wikipedia" in u for u in uris)

    def test_wikipedia_link_on_page_3(self, pdf_long):
        """The Wikipedia fish link is on page 3."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_long)
        wiki_records = [r for r in records if "wikipedia" in r.uri]
        assert len(wiki_records) >= 1
        assert wiki_records[0].page == 3

    def test_error_records_present_on_timeout(self, pdf_long):
        """Timeout errors are captured and the error field is populated."""
        import requests as req

        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_long)

        checker = RequestsLinkChecker()
        with patch.object(
            checker._session,
            "get",
            side_effect=req.exceptions.Timeout("simulated timeout"),
        ):
            concurrent = ConcurrentLinkChecker(strategy=checker)
            resolved = concurrent.check_all(records)

        for r in resolved:
            assert r.status is None
            assert "Timeout" in r.error


# ---------------------------------------------------------------------------
# run() CLI function integration
# ---------------------------------------------------------------------------

class TestRunFunction:
    """Integration tests for the cli.run() orchestration function."""

    @patch("pdf_link_checker.cli.ConcurrentLinkChecker")
    def test_run_creates_csv_report(self, mock_checker_cls, pdf_short, tmp_path):
        """run() creates a CSV file when given a .csv output path."""
        resolved = [
            LinkRecord(page=1, uri="https://example.com", status=200, error="NA")
        ]
        mock_checker_cls.return_value.check_all.return_value = resolved

        out = tmp_path / "report.csv"
        run(pdf=pdf_short, output=out, timeout=5.0, workers=2)
        assert out.exists()

    @patch("pdf_link_checker.cli.ConcurrentLinkChecker")
    def test_run_creates_json_report(self, mock_checker_cls, pdf_short, tmp_path):
        """run() creates a JSON file when given a .json output path."""
        resolved = [
            LinkRecord(page=1, uri="https://example.com", status=200, error="NA")
        ]
        mock_checker_cls.return_value.check_all.return_value = resolved

        out = tmp_path / "report.json"
        run(pdf=pdf_short, output=out, timeout=5.0, workers=2)
        assert out.exists()

    @patch("pdf_link_checker.cli.ConcurrentLinkChecker")
    def test_run_returns_resolved_records(self, mock_checker_cls, pdf_short, tmp_path):
        """run() returns the list of resolved LinkRecords."""
        resolved = [
            LinkRecord(page=1, uri="https://example.com", status=200, error="NA")
        ]
        mock_checker_cls.return_value.check_all.return_value = resolved

        result = run(pdf=pdf_short, output=tmp_path / "report.csv")
        assert result == resolved

    def test_run_raises_for_missing_pdf(self, tmp_path):
        """run() raises FileNotFoundError for a non-existent PDF."""
        with pytest.raises(FileNotFoundError):
            run(pdf=tmp_path / "ghost.pdf", output=tmp_path / "out.csv")

    def test_run_raises_for_unsupported_format(self, pdf_short, tmp_path):
        """run() raises ValueError for an unsupported output format."""
        with pytest.raises(ValueError, match="Unsupported output format"):
            run(pdf=pdf_short, output=tmp_path / "report.xlsx")
