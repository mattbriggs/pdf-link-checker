"""
Unit tests for pdf_link_checker.checker.

All HTTP calls are mocked via unittest.mock so these tests run
completely offline and deterministically.
"""

from unittest.mock import MagicMock, patch, PropertyMock
import pytest
import requests

from pdf_link_checker.checker import RequestsLinkChecker, ConcurrentLinkChecker
from pdf_link_checker.models import LinkRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(page: int = 1, uri: str = "https://example.com") -> LinkRecord:
    return LinkRecord(page=page, uri=uri, status=None)


def _mock_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


# ---------------------------------------------------------------------------
# RequestsLinkChecker
# ---------------------------------------------------------------------------

class TestRequestsLinkCheckerSuccess:
    """Tests for successful HTTP responses."""

    def test_returns_link_record(self):
        """check() always returns a LinkRecord."""
        checker = RequestsLinkChecker()
        with patch.object(checker._session, "get", return_value=_mock_response(200)):
            result = checker.check(_make_record())
        assert isinstance(result, LinkRecord)

    def test_status_200_recorded(self):
        """check() records HTTP 200 status."""
        checker = RequestsLinkChecker()
        with patch.object(checker._session, "get", return_value=_mock_response(200)):
            result = checker.check(_make_record())
        assert result.status == 200

    def test_status_404_recorded(self):
        """check() records HTTP 404 status without treating it as an error."""
        checker = RequestsLinkChecker()
        with patch.object(checker._session, "get", return_value=_mock_response(404)):
            result = checker.check(_make_record())
        assert result.status == 404
        assert result.error == "NA"

    def test_status_301_recorded(self):
        """check() records the final status after following a redirect."""
        checker = RequestsLinkChecker()
        with patch.object(checker._session, "get", return_value=_mock_response(301)):
            result = checker.check(_make_record())
        assert result.status == 301

    def test_error_is_na_on_success(self):
        """check() sets error='NA' for successful requests."""
        checker = RequestsLinkChecker()
        with patch.object(checker._session, "get", return_value=_mock_response(200)):
            result = checker.check(_make_record())
        assert result.error == "NA"

    def test_page_number_preserved(self):
        """check() preserves the page number from the input record."""
        checker = RequestsLinkChecker()
        record = _make_record(page=7)
        with patch.object(checker._session, "get", return_value=_mock_response(200)):
            result = checker.check(record)
        assert result.page == 7

    def test_uri_preserved(self):
        """check() preserves the original URI (including any whitespace)."""
        uri = " https://example.com/path "
        checker = RequestsLinkChecker()
        record = _make_record(uri=uri)
        with patch.object(checker._session, "get", return_value=_mock_response(200)):
            result = checker.check(record)
        assert result.uri == uri

    def test_uri_stripped_before_request(self):
        """check() strips leading/trailing whitespace before making the request."""
        uri = " https://example.com "
        checker = RequestsLinkChecker()
        record = _make_record(uri=uri)
        with patch.object(checker._session, "get", return_value=_mock_response(200)) as mock_get:
            checker.check(record)
        mock_get.assert_called_once_with(
            "https://example.com",
            timeout=checker.timeout,
            stream=True,
            allow_redirects=True,
        )


class TestRequestsLinkCheckerErrors:
    """Tests for request failure scenarios."""

    def test_timeout_sets_status_none(self):
        """A Timeout exception causes status=None."""
        checker = RequestsLinkChecker()
        with patch.object(
            checker._session,
            "get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            result = checker.check(_make_record())
        assert result.status is None

    def test_timeout_error_message_recorded(self):
        """A Timeout exception populates the error field."""
        checker = RequestsLinkChecker()
        with patch.object(
            checker._session,
            "get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            result = checker.check(_make_record())
        assert "Timeout" in result.error

    def test_connection_error_sets_status_none(self):
        """A ConnectionError exception causes status=None."""
        checker = RequestsLinkChecker()
        with patch.object(
            checker._session,
            "get",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            result = checker.check(_make_record())
        assert result.status is None

    def test_connection_error_message_recorded(self):
        """A ConnectionError exception populates the error field."""
        checker = RequestsLinkChecker()
        with patch.object(
            checker._session,
            "get",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            result = checker.check(_make_record())
        assert "ConnectionError" in result.error

    def test_generic_request_exception_sets_status_none(self):
        """A generic RequestException causes status=None."""
        checker = RequestsLinkChecker()
        with patch.object(
            checker._session,
            "get",
            side_effect=requests.exceptions.RequestException("generic error"),
        ):
            result = checker.check(_make_record())
        assert result.status is None

    def test_generic_request_exception_error_message_recorded(self):
        """A generic RequestException populates the error field."""
        checker = RequestsLinkChecker()
        with patch.object(
            checker._session,
            "get",
            side_effect=requests.exceptions.RequestException("generic error"),
        ):
            result = checker.check(_make_record())
        assert "RequestException" in result.error


class TestRequestsLinkCheckerInit:
    """Tests for RequestsLinkChecker initialisation."""

    def test_default_timeout(self):
        """Default timeout is 5.0 seconds."""
        checker = RequestsLinkChecker()
        assert checker.timeout == 5.0

    def test_custom_timeout(self):
        """Custom timeout is stored."""
        checker = RequestsLinkChecker(timeout=10.0)
        assert checker.timeout == 10.0

    def test_custom_session_used(self):
        """A provided session is stored and used."""
        session = requests.Session()
        checker = RequestsLinkChecker(session=session)
        assert checker._session is session


# ---------------------------------------------------------------------------
# ConcurrentLinkChecker
# ---------------------------------------------------------------------------

class TestConcurrentLinkChecker:
    """Tests for ConcurrentLinkChecker orchestration."""

    def _make_strategy(self, status: int = 200) -> MagicMock:
        strategy = MagicMock()
        strategy.check.side_effect = lambda r: LinkRecord(
            page=r.page, uri=r.uri, status=status, error="NA"
        )
        return strategy

    def test_returns_list(self):
        """check_all() returns a list."""
        checker = ConcurrentLinkChecker(strategy=self._make_strategy())
        result = checker.check_all([_make_record()])
        assert isinstance(result, list)

    def test_empty_input_returns_empty_list(self):
        """check_all() returns an empty list for empty input."""
        checker = ConcurrentLinkChecker(strategy=self._make_strategy())
        assert checker.check_all([]) == []

    def test_same_count_in_and_out(self):
        """check_all() returns the same number of records as input."""
        records = [_make_record(page=i) for i in range(1, 6)]
        checker = ConcurrentLinkChecker(strategy=self._make_strategy())
        result = checker.check_all(records)
        assert len(result) == 5

    def test_results_sorted_by_page(self):
        """check_all() returns records sorted ascending by page number."""
        records = [_make_record(page=i) for i in range(5, 0, -1)]
        checker = ConcurrentLinkChecker(strategy=self._make_strategy())
        result = checker.check_all(records)
        pages = [r.page for r in result]
        assert pages == sorted(pages)

    def test_strategy_called_for_each_record(self):
        """The strategy's check() method is called once per input record."""
        records = [_make_record(page=i) for i in range(1, 4)]
        strategy = self._make_strategy()
        checker = ConcurrentLinkChecker(strategy=strategy)
        checker.check_all(records)
        assert strategy.check.call_count == 3

    def test_progress_callback_invoked(self):
        """The progress_callback is called once per resolved record."""
        calls = []
        records = [_make_record(page=i) for i in range(1, 4)]
        checker = ConcurrentLinkChecker(
            strategy=self._make_strategy(),
            progress_callback=calls.append,
        )
        checker.check_all(records)
        assert len(calls) == 3

    def test_resolved_records_have_status(self):
        """All resolved records have a non-None status after check_all()."""
        records = [_make_record(page=i) for i in range(1, 4)]
        checker = ConcurrentLinkChecker(strategy=self._make_strategy(status=200))
        result = checker.check_all(records)
        for r in result:
            assert r.status == 200
