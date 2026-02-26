"""
PDF link extraction strategies.

Provides Strategy-pattern implementations for extracting hyperlinks from PDF
documents. New PDF backends can be added by subclassing
:class:`PDFExtractorStrategy` without changing any other part of the system.
"""

import logging
import pathlib
from abc import ABC, abstractmethod
from typing import List

import pypdf

from .models import LinkRecord

logger = logging.getLogger(__name__)


class PDFExtractorStrategy(ABC):
    """Abstract base class defining the interface for PDF link extraction.

    All concrete extractors must implement :meth:`extract_links`. They should
    return :class:`~pdf_link_checker.models.LinkRecord` objects whose
    :attr:`~pdf_link_checker.models.LinkRecord.status` is ``None`` — status
    resolution is the responsibility of the checker layer.
    """

    @abstractmethod
    def extract_links(self, pdf_path: pathlib.Path) -> List[LinkRecord]:
        """Extract all hyperlinks from a PDF file.

        :param pdf_path: Path to the PDF file to analyse.
        :type pdf_path: pathlib.Path
        :returns: A list of :class:`~pdf_link_checker.models.LinkRecord`
            objects with ``status=None`` and ``error='NA'``.
        :rtype: List[LinkRecord]
        :raises FileNotFoundError: If *pdf_path* does not exist.
        :raises ValueError: If the file cannot be parsed as a PDF.
        """


class PyPDFExtractor(PDFExtractorStrategy):
    """PDF link extractor backed by the ``pypdf`` library.

    Iterates every page of the document, inspects annotation objects for
    URI actions (``/A`` → ``/URI``), and returns one
    :class:`~pdf_link_checker.models.LinkRecord` per discovered hyperlink.

    This extractor replaces the deprecated ``PyPDF2`` library with the
    actively-maintained ``pypdf`` successor and uses its current API
    (``pypdf.PdfReader``, ``reader.pages``).

    Example::

        extractor = PyPDFExtractor()
        records = extractor.extract_links(pathlib.Path("document.pdf"))
        for record in records:
            print(record.page, record.uri)
    """

    def extract_links(self, pdf_path: pathlib.Path) -> List[LinkRecord]:
        """Extract hyperlinks from *pdf_path* using ``pypdf``.

        :param pdf_path: Absolute or relative path to the PDF file.
        :type pdf_path: pathlib.Path
        :returns: Unresolved link records (``status`` is ``None``).
        :rtype: List[LinkRecord]
        :raises FileNotFoundError: If *pdf_path* does not exist on disk.
        :raises pypdf.errors.PdfReadError: If the PDF cannot be parsed.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        records: List[LinkRecord] = []
        logger.info("Opening PDF: %s", pdf_path)

        reader = pypdf.PdfReader(str(pdf_path))
        num_pages = len(reader.pages)
        logger.info("PDF contains %d page(s)", num_pages)

        for page_index, page in enumerate(reader.pages):
            page_no = page_index + 1
            annots = page.get("/Annots")

            if annots is None:
                logger.debug("Page %d: no annotations", page_no)
                continue

            for annot_ref in annots:
                try:
                    annot_obj = annot_ref.get_object()
                except Exception:
                    logger.debug("Page %d: could not dereference annotation", page_no)
                    continue

                action = annot_obj.get("/A")
                if action is None:
                    continue

                # Dereference the action if it is an indirect object
                if hasattr(action, "get_object"):
                    action = action.get_object()

                uri = action.get("/URI")
                if uri:
                    logger.debug("Page %d: found URI %s", page_no, uri)
                    records.append(
                        LinkRecord(page=page_no, uri=str(uri), status=None)
                    )

        logger.info("Extracted %d link(s) from %s", len(records), pdf_path)
        return records
