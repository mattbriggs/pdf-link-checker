"""
Report writer strategies and factory.

Provides Strategy-pattern implementations for serialising link-check results
to various file formats, and a Factory for selecting the correct writer based
on the output file extension.
"""

import csv
import json
import logging
import pathlib
from abc import ABC, abstractmethod
from typing import Dict, List, Type

from .models import LinkRecord

logger = logging.getLogger(__name__)

#: Column header row used by all tabular report writers.
REPORT_HEADER: List[str] = ["page", "uri", "status", "request-error"]


class ReportWriterStrategy(ABC):
    """Abstract base class for report writer strategies.

    Each concrete writer serialises a list of
    :class:`~pdf_link_checker.models.LinkRecord` objects to a specific file
    format. The output directory is created automatically if it does not exist.
    """

    @abstractmethod
    def write(self, records: List[LinkRecord], output_path: pathlib.Path) -> None:
        """Write *records* to *output_path*.

        :param records: Resolved link-check results to serialise.
        :type records: List[LinkRecord]
        :param output_path: Destination file path.
        :type output_path: pathlib.Path
        :raises OSError: If the file cannot be created or written to.
        """


class CSVReportWriter(ReportWriterStrategy):
    """Writes link-check results to a UTF-8 CSV file.

    The output includes a header row followed by one data row per
    :class:`~pdf_link_checker.models.LinkRecord`. Line endings are handled
    by Python's :mod:`csv` module, ensuring cross-platform compatibility.

    Example::

        writer = CSVReportWriter()
        writer.write(records, pathlib.Path("report.csv"))
    """

    def write(self, records: List[LinkRecord], output_path: pathlib.Path) -> None:
        """Write results to a CSV file at *output_path*.

        :param records: Resolved link-check results.
        :type records: List[LinkRecord]
        :param output_path: Destination ``.csv`` file path.
        :type output_path: pathlib.Path
        :raises OSError: If the file cannot be opened for writing.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(REPORT_HEADER)
            for record in records:
                writer.writerow(record.as_row())
        logger.info("CSV report written: %s (%d record(s))", output_path, len(records))


class JSONReportWriter(ReportWriterStrategy):
    """Writes link-check results to a UTF-8 JSON file.

    The output is a JSON array where each element is an object with keys
    ``page``, ``uri``, ``status``, and ``error``.

    Example::

        writer = JSONReportWriter()
        writer.write(records, pathlib.Path("report.json"))
    """

    def write(self, records: List[LinkRecord], output_path: pathlib.Path) -> None:
        """Write results to a JSON file at *output_path*.

        :param records: Resolved link-check results.
        :type records: List[LinkRecord]
        :param output_path: Destination ``.json`` file path.
        :type output_path: pathlib.Path
        :raises OSError: If the file cannot be opened for writing.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "page": r.page,
                "uri": r.uri,
                "status": r.status,
                "error": r.error,
            }
            for r in records
        ]
        with open(output_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=2)
        logger.info("JSON report written: %s (%d record(s))", output_path, len(records))


class ReportWriterFactory:
    """Factory that creates :class:`ReportWriterStrategy` instances.

    The appropriate writer is selected by matching the file extension of
    *output_path*. New formats can be registered by updating
    :attr:`_registry` or subclassing this factory.

    Supported extensions:

    * ``.csv`` → :class:`CSVReportWriter`
    * ``.json`` → :class:`JSONReportWriter`

    :raises ValueError: When the file extension is not in the registry.

    Example::

        writer = ReportWriterFactory.create(pathlib.Path("report.csv"))
        writer.write(records, pathlib.Path("report.csv"))
    """

    _registry: Dict[str, Type[ReportWriterStrategy]] = {
        ".csv": CSVReportWriter,
        ".json": JSONReportWriter,
    }

    @classmethod
    def create(cls, output_path: pathlib.Path) -> ReportWriterStrategy:
        """Return a writer appropriate for *output_path*'s file extension.

        :param output_path: The intended output file path. Only the suffix
            is inspected; the file does not need to exist.
        :type output_path: pathlib.Path
        :returns: A concrete :class:`ReportWriterStrategy` instance.
        :rtype: ReportWriterStrategy
        :raises ValueError: If the extension is not ``.csv`` or ``.json``.
        """
        ext = output_path.suffix.lower()
        writer_class = cls._registry.get(ext)
        if writer_class is None:
            supported = ", ".join(sorted(cls._registry.keys()))
            raise ValueError(
                f"Unsupported output format '{ext}'. "
                f"Supported formats: {supported}"
            )
        return writer_class()
