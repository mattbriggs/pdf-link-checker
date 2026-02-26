"""
Unit tests for pdf_link_checker.reporter.

Tests cover CSV and JSON writers, the ReportWriterFactory, and edge cases
such as empty record lists and parent directory creation. All I/O uses
pytest's tmp_path fixture to avoid touching the project tree.
"""

import csv
import json
import pathlib

import pytest

from pdf_link_checker.models import LinkRecord
from pdf_link_checker.reporter import (
    CSVReportWriter,
    JSONReportWriter,
    ReportWriterFactory,
    REPORT_HEADER,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _records():
    return [
        LinkRecord(page=1, uri="https://example.com", status=200, error="NA"),
        LinkRecord(page=2, uri="https://missing.example.com", status=404, error="NA"),
        LinkRecord(page=3, uri="https://bad.url", status=None, error="Timeout: …"),
    ]


# ---------------------------------------------------------------------------
# CSVReportWriter
# ---------------------------------------------------------------------------

class TestCSVReportWriter:
    """Tests for CSVReportWriter."""

    def test_creates_file(self, tmp_path):
        """write() creates the output CSV file."""
        out = tmp_path / "report.csv"
        CSVReportWriter().write(_records(), out)
        assert out.exists()

    def test_header_row_present(self, tmp_path):
        """The first row of the CSV matches REPORT_HEADER."""
        out = tmp_path / "report.csv"
        CSVReportWriter().write(_records(), out)
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows[0] == REPORT_HEADER

    def test_correct_number_of_data_rows(self, tmp_path):
        """The CSV contains one data row per record plus the header."""
        records = _records()
        out = tmp_path / "report.csv"
        CSVReportWriter().write(records, out)
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == len(records) + 1

    def test_status_200_in_csv(self, tmp_path):
        """A 200 status is written as the string '200'."""
        out = tmp_path / "report.csv"
        CSVReportWriter().write(_records(), out)
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows[1][2] == "200"

    def test_none_status_written_as_na(self, tmp_path):
        """A None status is written as 'NA' in the CSV."""
        records = [LinkRecord(page=1, uri="https://bad.url", status=None, error="Timeout")]
        out = tmp_path / "report.csv"
        CSVReportWriter().write(records, out)
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows[1][2] == "NA"

    def test_creates_parent_directories(self, tmp_path):
        """write() creates any missing parent directories."""
        out = tmp_path / "nested" / "deep" / "report.csv"
        CSVReportWriter().write(_records(), out)
        assert out.exists()

    def test_empty_records_writes_header_only(self, tmp_path):
        """An empty records list writes only the header row."""
        out = tmp_path / "empty.csv"
        CSVReportWriter().write([], out)
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 1
        assert rows[0] == REPORT_HEADER


# ---------------------------------------------------------------------------
# JSONReportWriter
# ---------------------------------------------------------------------------

class TestJSONReportWriter:
    """Tests for JSONReportWriter."""

    def test_creates_file(self, tmp_path):
        """write() creates the output JSON file."""
        out = tmp_path / "report.json"
        JSONReportWriter().write(_records(), out)
        assert out.exists()

    def test_output_is_valid_json(self, tmp_path):
        """The output file can be parsed as valid JSON."""
        out = tmp_path / "report.json"
        JSONReportWriter().write(_records(), out)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)

    def test_correct_number_of_items(self, tmp_path):
        """The JSON array contains one entry per record."""
        records = _records()
        out = tmp_path / "report.json"
        JSONReportWriter().write(records, out)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == len(records)

    def test_json_keys_present(self, tmp_path):
        """Each JSON object has the expected keys."""
        out = tmp_path / "report.json"
        JSONReportWriter().write(_records(), out)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            assert set(item.keys()) == {"page", "uri", "status", "error"}

    def test_none_status_serialised_as_null(self, tmp_path):
        """A None status is serialised as JSON null."""
        records = [LinkRecord(page=1, uri="https://bad.url", status=None, error="Timeout")]
        out = tmp_path / "report.json"
        JSONReportWriter().write(records, out)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        assert data[0]["status"] is None

    def test_creates_parent_directories(self, tmp_path):
        """write() creates any missing parent directories."""
        out = tmp_path / "nested" / "report.json"
        JSONReportWriter().write(_records(), out)
        assert out.exists()

    def test_empty_records_writes_empty_array(self, tmp_path):
        """An empty records list writes a JSON empty array '[]'."""
        out = tmp_path / "empty.json"
        JSONReportWriter().write([], out)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        assert data == []


# ---------------------------------------------------------------------------
# ReportWriterFactory
# ---------------------------------------------------------------------------

class TestReportWriterFactory:
    """Tests for the ReportWriterFactory."""

    def test_creates_csv_writer_for_csv_extension(self, tmp_path):
        """Factory returns CSVReportWriter for a .csv path."""
        writer = ReportWriterFactory.create(tmp_path / "out.csv")
        assert isinstance(writer, CSVReportWriter)

    def test_creates_json_writer_for_json_extension(self, tmp_path):
        """Factory returns JSONReportWriter for a .json path."""
        writer = ReportWriterFactory.create(tmp_path / "out.json")
        assert isinstance(writer, JSONReportWriter)

    def test_extension_case_insensitive(self, tmp_path):
        """Factory handles uppercase extensions (.CSV, .JSON)."""
        writer_csv = ReportWriterFactory.create(tmp_path / "out.CSV")
        assert isinstance(writer_csv, CSVReportWriter)
        writer_json = ReportWriterFactory.create(tmp_path / "out.JSON")
        assert isinstance(writer_json, JSONReportWriter)

    def test_raises_for_unsupported_extension(self, tmp_path):
        """Factory raises ValueError for an unsupported extension."""
        with pytest.raises(ValueError, match="Unsupported output format"):
            ReportWriterFactory.create(tmp_path / "out.xlsx")

    def test_raises_for_no_extension(self, tmp_path):
        """Factory raises ValueError when the path has no extension."""
        with pytest.raises(ValueError):
            ReportWriterFactory.create(tmp_path / "report")
