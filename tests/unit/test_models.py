"""
Unit tests for pdf_link_checker.models.

Tests cover the LinkRecord dataclass including construction, defaults,
and the as_row() serialisation helper.
"""

import pytest
from pdf_link_checker.models import LinkRecord


class TestLinkRecordConstruction:
    """Tests for basic LinkRecord creation and field values."""

    def test_creation_with_all_fields(self):
        """LinkRecord stores all provided field values correctly."""
        record = LinkRecord(page=1, uri="https://example.com", status=200, error="NA")
        assert record.page == 1
        assert record.uri == "https://example.com"
        assert record.status == 200
        assert record.error == "NA"

    def test_default_error_is_na(self):
        """The error field defaults to 'NA' when not provided."""
        record = LinkRecord(page=5, uri="https://example.com", status=404)
        assert record.error == "NA"

    def test_status_can_be_none(self):
        """status accepts None to represent an unresolved or failed check."""
        record = LinkRecord(page=1, uri="https://example.com", status=None)
        assert record.status is None

    def test_uri_stores_leading_whitespace(self):
        """URIs are stored verbatim, including any embedded whitespace."""
        uri = " http://example.com"
        record = LinkRecord(page=1, uri=uri, status=200)
        assert record.uri == uri

    def test_page_number_stored(self):
        """Page number is stored as provided."""
        record = LinkRecord(page=42, uri="https://example.com", status=200)
        assert record.page == 42


class TestLinkRecordAsRow:
    """Tests for the as_row() serialisation method."""

    def test_as_row_with_integer_status(self):
        """as_row() returns the status integer when status is set."""
        record = LinkRecord(page=3, uri="https://example.com", status=200, error="NA")
        assert record.as_row() == [3, "https://example.com", 200, "NA"]

    def test_as_row_with_none_status_returns_na_string(self):
        """as_row() substitutes 'NA' when status is None."""
        record = LinkRecord(
            page=2, uri="https://example.com", status=None, error="Timeout"
        )
        row = record.as_row()
        assert row[2] == "NA"

    def test_as_row_preserves_error_message(self):
        """as_row() includes the error string in the fourth position."""
        error_msg = "ConnectionError: [Errno 8] Name or service not known"
        record = LinkRecord(page=1, uri="https://bad.url", status=None, error=error_msg)
        assert record.as_row()[3] == error_msg

    def test_as_row_returns_four_elements(self):
        """as_row() always returns a list of exactly four elements."""
        record = LinkRecord(page=1, uri="https://example.com", status=200)
        assert len(record.as_row()) == 4

    def test_as_row_page_is_first_element(self):
        """The first element of as_row() is the page number."""
        record = LinkRecord(page=7, uri="https://example.com", status=200)
        assert record.as_row()[0] == 7

    def test_as_row_uri_is_second_element(self):
        """The second element of as_row() is the URI string."""
        record = LinkRecord(page=1, uri="https://example.com/path", status=200)
        assert record.as_row()[1] == "https://example.com/path"

    def test_as_row_404_status_preserved(self):
        """as_row() preserves non-200 status codes like 404."""
        record = LinkRecord(page=1, uri="https://example.com/missing", status=404)
        assert record.as_row()[2] == 404
