"""
Unit tests for pdf_link_checker.cli.

Tests cover argument parser construction, _configure_logging,
_build_progress_callback, run(), and main(). HTTP calls and PDF extraction
are mocked so these tests run fully offline.
"""

import logging
import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from pdf_link_checker.cli import (
    build_arg_parser,
    run,
    main,
    _configure_logging,
    _build_progress_callback,
)
from pdf_link_checker.models import LinkRecord


class TestBuildArgParser:
    """Tests for build_arg_parser()."""

    def test_returns_parser(self):
        """build_arg_parser() returns an ArgumentParser instance."""
        import argparse
        parser = build_arg_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parses_pdf_and_output(self, tmp_path):
        """Parser correctly handles positional pdf and output arguments."""
        parser = build_arg_parser()
        pdf = tmp_path / "test.pdf"
        out = tmp_path / "report.csv"
        args = parser.parse_args([str(pdf), str(out)])
        assert args.pdf == pdf
        assert args.output == out

    def test_default_timeout(self, tmp_path):
        """Default timeout is 5.0."""
        parser = build_arg_parser()
        args = parser.parse_args([str(tmp_path / "a.pdf"), str(tmp_path / "b.csv")])
        assert args.timeout == 5.0

    def test_custom_timeout(self, tmp_path):
        """--timeout sets the timeout value."""
        parser = build_arg_parser()
        args = parser.parse_args([
            str(tmp_path / "a.pdf"), str(tmp_path / "b.csv"), "--timeout", "10.0"
        ])
        assert args.timeout == 10.0

    def test_default_workers(self, tmp_path):
        """Default worker count is 4."""
        parser = build_arg_parser()
        args = parser.parse_args([str(tmp_path / "a.pdf"), str(tmp_path / "b.csv")])
        assert args.workers == 4

    def test_custom_workers(self, tmp_path):
        """--workers sets the worker count."""
        parser = build_arg_parser()
        args = parser.parse_args([
            str(tmp_path / "a.pdf"), str(tmp_path / "b.csv"), "--workers", "8"
        ])
        assert args.workers == 8

    def test_verbose_flag_false_by_default(self, tmp_path):
        """--verbose is False when not supplied."""
        parser = build_arg_parser()
        args = parser.parse_args([str(tmp_path / "a.pdf"), str(tmp_path / "b.csv")])
        assert args.verbose is False

    def test_verbose_flag_true_when_supplied(self, tmp_path):
        """--verbose is True when the flag is passed."""
        parser = build_arg_parser()
        args = parser.parse_args([
            str(tmp_path / "a.pdf"), str(tmp_path / "b.csv"), "--verbose"
        ])
        assert args.verbose is True

    def test_short_verbose_flag(self, tmp_path):
        """-v is an alias for --verbose."""
        parser = build_arg_parser()
        args = parser.parse_args([str(tmp_path / "a.pdf"), str(tmp_path / "b.csv"), "-v"])
        assert args.verbose is True


class TestRunFunction:
    """Tests for the run() pipeline function with mocked dependencies."""

    def _make_records(self):
        return [
            LinkRecord(page=1, uri="https://example.com", status=None),
            LinkRecord(page=2, uri="https://other.example.com", status=None),
        ]

    def _resolved(self, records):
        return [
            LinkRecord(page=r.page, uri=r.uri, status=200, error="NA")
            for r in records
        ]

    @patch("pdf_link_checker.cli.PyPDFExtractor")
    @patch("pdf_link_checker.cli.ConcurrentLinkChecker")
    @patch("pdf_link_checker.cli.ReportWriterFactory")
    def test_run_returns_list(self, mock_factory, mock_checker_cls, mock_extractor_cls, tmp_path):
        """run() returns a list of resolved LinkRecords."""
        records = self._make_records()
        resolved = self._resolved(records)

        mock_extractor_cls.return_value.extract_links.return_value = records
        mock_checker_cls.return_value.check_all.return_value = resolved
        mock_factory.create.return_value.write = MagicMock()

        pdf = tmp_path / "dummy.pdf"
        pdf.touch()
        result = run(pdf=pdf, output=tmp_path / "out.csv")
        assert isinstance(result, list)
        assert len(result) == 2

    @patch("pdf_link_checker.cli.PyPDFExtractor")
    @patch("pdf_link_checker.cli.ReportWriterFactory")
    def test_run_empty_pdf_returns_empty_list(
        self, mock_factory, mock_extractor_cls, tmp_path
    ):
        """run() returns an empty list when no links are found."""
        mock_extractor_cls.return_value.extract_links.return_value = []
        mock_factory.create.return_value.write = MagicMock()

        pdf = tmp_path / "empty.pdf"
        pdf.touch()
        result = run(pdf=pdf, output=tmp_path / "out.csv")
        assert result == []

    @patch("pdf_link_checker.cli.PyPDFExtractor")
    def test_run_raises_file_not_found(self, mock_extractor_cls, tmp_path):
        """run() propagates FileNotFoundError from the extractor."""
        mock_extractor_cls.return_value.extract_links.side_effect = FileNotFoundError(
            "PDF not found"
        )
        with pytest.raises(FileNotFoundError):
            run(pdf=tmp_path / "missing.pdf", output=tmp_path / "out.csv")


class TestConfigureLogging:
    """Tests for _configure_logging()."""

    def test_sets_debug_level_when_verbose(self):
        """_configure_logging(True) configures DEBUG level."""
        with patch("pdf_link_checker.cli.logging.basicConfig") as mock_bc:
            _configure_logging(True)
        mock_bc.assert_called_once()
        call_kwargs = mock_bc.call_args[1]
        assert call_kwargs["level"] == logging.DEBUG

    def test_sets_info_level_when_not_verbose(self):
        """_configure_logging(False) configures INFO level."""
        with patch("pdf_link_checker.cli.logging.basicConfig") as mock_bc:
            _configure_logging(False)
        mock_bc.assert_called_once()
        call_kwargs = mock_bc.call_args[1]
        assert call_kwargs["level"] == logging.INFO


class TestBuildProgressCallback:
    """Tests for _build_progress_callback()."""

    def test_returns_callable(self):
        """_build_progress_callback() returns a callable."""
        cb = _build_progress_callback()
        assert callable(cb)

    def test_callback_prints_status(self, capsys):
        """The callback prints the page, status, and URI."""
        cb = _build_progress_callback()
        record = LinkRecord(page=1, uri="https://example.com", status=200, error="NA")
        cb(record)
        captured = capsys.readouterr()
        assert "200" in captured.out
        assert "https://example.com" in captured.out

    def test_callback_prints_err_for_none_status(self, capsys):
        """The callback prints 'ERR' when status is None."""
        cb = _build_progress_callback()
        record = LinkRecord(page=1, uri="https://bad.url", status=None, error="Timeout")
        cb(record)
        captured = capsys.readouterr()
        assert "ERR" in captured.out


class TestMainFunction:
    """Tests for the main() CLI entry point."""

    @patch("pdf_link_checker.cli.run")
    @patch("pdf_link_checker.cli._configure_logging")
    def test_main_calls_run(self, mock_log, mock_run, tmp_path):
        """main() calls run() with the parsed arguments."""
        pdf = tmp_path / "test.pdf"
        out = tmp_path / "report.csv"
        mock_run.return_value = []
        with patch("sys.argv", ["pdf-link-checker", str(pdf), str(out)]):
            main()
        mock_run.assert_called_once()

    @patch("pdf_link_checker.cli.run")
    @patch("pdf_link_checker.cli._configure_logging")
    def test_main_exits_1_on_file_not_found(self, mock_log, mock_run, tmp_path):
        """main() exits with code 1 when PDF is not found."""
        mock_run.side_effect = FileNotFoundError("not found")
        pdf = tmp_path / "ghost.pdf"
        out = tmp_path / "out.csv"
        with patch("sys.argv", ["pdf-link-checker", str(pdf), str(out)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

    @patch("pdf_link_checker.cli.run")
    @patch("pdf_link_checker.cli._configure_logging")
    def test_main_exits_1_on_value_error(self, mock_log, mock_run, tmp_path):
        """main() exits with code 1 on unsupported output format."""
        mock_run.side_effect = ValueError("Unsupported output format")
        pdf = tmp_path / "test.pdf"
        out = tmp_path / "out.xlsx"
        with patch("sys.argv", ["pdf-link-checker", str(pdf), str(out)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

    @patch("pdf_link_checker.cli.run")
    @patch("pdf_link_checker.cli._configure_logging")
    def test_main_exits_130_on_keyboard_interrupt(self, mock_log, mock_run, tmp_path):
        """main() exits with code 130 on KeyboardInterrupt."""
        mock_run.side_effect = KeyboardInterrupt()
        pdf = tmp_path / "test.pdf"
        out = tmp_path / "out.csv"
        with patch("sys.argv", ["pdf-link-checker", str(pdf), str(out)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 130
