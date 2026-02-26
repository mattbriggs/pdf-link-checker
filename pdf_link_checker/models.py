"""
Data models for the PDF Link Checker.

Defines the data transfer objects (DTOs) used throughout the application
to carry link-check results between the extraction, checking, and reporting
layers.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LinkRecord:
    """Represents a single hyperlink found in a PDF document.

    This is the primary data transfer object (DTO) passed between the
    extraction, checking, and reporting layers of the application.

    :param page: The 1-based page number where the link was found.
    :type page: int
    :param uri: The raw URI string extracted from the PDF annotation.
    :type uri: str
    :param status: The HTTP status code returned by the request, or
        ``None`` when the request failed or has not yet been made.
    :type status: int or None
    :param error: A human-readable description of any request error.
        Defaults to ``'NA'`` when no error occurred.
    :type error: str

    Example::

        record = LinkRecord(page=1, uri="https://example.com", status=200)
        print(record.as_row())
        # [1, 'https://example.com', 200, 'NA']
    """

    page: int
    uri: str
    status: Optional[int]
    error: str = field(default="NA")

    def as_row(self) -> list:
        """Return the record as a flat list suitable for CSV output.

        :returns: A four-element list ``[page, uri, status, error]``.
            When :attr:`status` is ``None`` the string ``'NA'`` is used.
        :rtype: list

        Example::

            record = LinkRecord(page=2, uri="https://example.com", status=None,
                                error="Timeout")
            record.as_row()
            # [2, 'https://example.com', 'NA', 'Timeout']
        """
        return [
            self.page,
            self.uri,
            self.status if self.status is not None else "NA",
            self.error,
        ]
