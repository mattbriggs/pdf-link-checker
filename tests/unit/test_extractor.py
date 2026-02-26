"""
Unit tests for pdf_link_checker.extractor.

Tests cover PyPDFExtractor behaviour with real test PDFs and edge cases
such as missing files, bad annotation references, and annotations without
URI actions. No network calls are made; these tests are purely local I/O.
"""

import pathlib
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from pdf_link_checker.extractor import PyPDFExtractor
from pdf_link_checker.models import LinkRecord


class TestPyPDFExtractorFileHandling:
    """Tests for file-level error handling in PyPDFExtractor."""

    def test_raises_file_not_found_for_missing_pdf(self, tmp_path):
        """extract_links raises FileNotFoundError for a non-existent path."""
        extractor = PyPDFExtractor()
        missing = tmp_path / "does_not_exist.pdf"
        with pytest.raises(FileNotFoundError, match="does_not_exist.pdf"):
            extractor.extract_links(missing)

    def test_accepts_pathlib_path(self, pdf_short):
        """extract_links accepts a pathlib.Path without raising."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)
        assert isinstance(records, list)

    def test_returns_list(self, pdf_short):
        """extract_links always returns a list."""
        extractor = PyPDFExtractor()
        result = extractor.extract_links(pdf_short)
        assert isinstance(result, list)


class TestPyPDFExtractorRecordStructure:
    """Tests that extracted records are correctly typed and structured."""

    def test_records_are_link_record_instances(self, pdf_short):
        """Every item in the returned list is a LinkRecord."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)
        assert len(records) > 0
        for record in records:
            assert isinstance(record, LinkRecord)

    def test_extracted_status_is_none(self, pdf_short):
        """Extracted records have status=None (not yet resolved)."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)
        for record in records:
            assert record.status is None

    def test_extracted_error_is_na(self, pdf_short):
        """Extracted records have error='NA' (not yet checked)."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)
        for record in records:
            assert record.error == "NA"

    def test_page_numbers_are_positive_integers(self, pdf_short):
        """All extracted page numbers are >= 1."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)
        for record in records:
            assert isinstance(record.page, int)
            assert record.page >= 1

    def test_uris_are_strings(self, pdf_short):
        """All extracted URIs are non-empty strings."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)
        for record in records:
            assert isinstance(record.uri, str)
            assert len(record.uri.strip()) > 0


class TestPyPDFExtractorShortPDF:
    """Tests against the short test PDF (pdflink.pdf, < 13 pages)."""

    def test_extracts_at_least_one_link(self, pdf_short):
        """The short PDF contains at least one hyperlink."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)
        assert len(records) >= 1

    def test_first_link_on_page_one(self, pdf_short):
        """The short PDF's first link is on page 1."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)
        assert records[0].page == 1

    def test_adobe_uri_present(self, pdf_short):
        """The short PDF contains the known Adobe URI (case-insensitive check)."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_short)
        uris = [r.uri.strip().lower() for r in records]
        assert any("adobe" in u for u in uris)


class TestPyPDFExtractorLongPDF:
    """Tests against the longer test PDF (testpdf.pdf, > 13 pages)."""

    def test_extracts_links_from_long_pdf(self, pdf_long):
        """The long PDF yields at least one hyperlink."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_long)
        assert len(records) >= 1

    def test_wikipedia_uri_present(self, pdf_long):
        """The long PDF contains the known Wikipedia fish URI."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_long)
        uris = [r.uri.strip() for r in records]
        assert any("wikipedia" in u for u in uris)

    def test_link_found_on_page_three(self, pdf_long):
        """The long PDF has a link on page 3."""
        extractor = PyPDFExtractor()
        records = extractor.extract_links(pdf_long)
        pages = [r.page for r in records]
        assert 3 in pages


class TestPyPDFExtractorEdgeCases:
    """Tests for defensive edge cases using mocked pypdf objects."""

    def _make_mock_reader(self, pages):
        """Return a mock PdfReader with the given list of mock page objects."""
        mock_reader = MagicMock()
        mock_reader.pages = pages
        return mock_reader

    def _make_page_with_bad_annot(self):
        """Return a page whose annotation raises on get_object()."""
        bad_annot = MagicMock()
        bad_annot.get_object.side_effect = Exception("corrupt annotation")
        page = MagicMock()
        page.get.return_value = [bad_annot]
        return page

    def _make_page_with_no_action_annot(self):
        """Return a page whose annotation has no /A key (no action)."""
        annot_obj = MagicMock()
        annot_obj.get.return_value = None  # /A is None
        annot_ref = MagicMock()
        annot_ref.get_object.return_value = annot_obj
        page = MagicMock()
        page.get.return_value = [annot_ref]
        return page

    def test_bad_annotation_dereference_skipped(self, tmp_path):
        """Annotations that raise on get_object() are silently skipped."""
        dummy_pdf = tmp_path / "dummy.pdf"
        dummy_pdf.touch()
        extractor = PyPDFExtractor()
        page = self._make_page_with_bad_annot()
        with patch("pdf_link_checker.extractor.pypdf.PdfReader") as mock_pdf_cls:
            mock_pdf_cls.return_value.pages = [page]
            records = extractor.extract_links(dummy_pdf)
        assert records == []

    def test_annotation_without_action_skipped(self, tmp_path):
        """Annotations without an /A action key produce no LinkRecord."""
        dummy_pdf = tmp_path / "dummy.pdf"
        dummy_pdf.touch()
        extractor = PyPDFExtractor()
        page = self._make_page_with_no_action_annot()
        with patch("pdf_link_checker.extractor.pypdf.PdfReader") as mock_pdf_cls:
            mock_pdf_cls.return_value.pages = [page]
            records = extractor.extract_links(dummy_pdf)
        assert records == []

    def test_page_with_no_annotations_produces_no_records(self, tmp_path):
        """A page whose /Annots key is missing produces no LinkRecord."""
        dummy_pdf = tmp_path / "dummy.pdf"
        dummy_pdf.touch()
        extractor = PyPDFExtractor()
        page = MagicMock()
        page.get.return_value = None  # /Annots is None
        with patch("pdf_link_checker.extractor.pypdf.PdfReader") as mock_pdf_cls:
            mock_pdf_cls.return_value.pages = [page]
            records = extractor.extract_links(dummy_pdf)
        assert records == []
