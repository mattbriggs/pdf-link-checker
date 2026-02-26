"""
pdf_link_checker
~~~~~~~~~~~~~~~~

A cross-platform command-line tool for extracting and validating hyperlinks
in PDF documents.

:version: 2.0.0
:author: Matt Briggs
:license: MIT
"""

__version__ = "2.0.0"
__author__ = "Matt Briggs"

from .models import LinkRecord
from .extractor import PDFExtractorStrategy, PyPDFExtractor
from .checker import LinkCheckerStrategy, RequestsLinkChecker, ConcurrentLinkChecker
from .reporter import ReportWriterStrategy, CSVReportWriter, JSONReportWriter, ReportWriterFactory

__all__ = [
    "LinkRecord",
    "PDFExtractorStrategy",
    "PyPDFExtractor",
    "LinkCheckerStrategy",
    "RequestsLinkChecker",
    "ConcurrentLinkChecker",
    "ReportWriterStrategy",
    "CSVReportWriter",
    "JSONReportWriter",
    "ReportWriterFactory",
]
