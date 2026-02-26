"""
HTTP link checking strategies.

Provides Strategy-pattern implementations for resolving HTTP status codes for
URIs extracted from PDF documents. Concurrent checking is orchestrated by
:class:`ConcurrentLinkChecker`, which uses
:mod:`concurrent.futures` to parallelise requests without shared mutable
state between worker threads.
"""

import concurrent.futures
import logging
from abc import ABC, abstractmethod
from typing import Callable, List, Optional

import requests

from .models import LinkRecord

logger = logging.getLogger(__name__)


class LinkCheckerStrategy(ABC):
    """Abstract base class for link checking strategies.

    A strategy receives a :class:`~pdf_link_checker.models.LinkRecord` whose
    ``status`` is ``None`` and returns a **new** record with
    :attr:`~pdf_link_checker.models.LinkRecord.status` and
    :attr:`~pdf_link_checker.models.LinkRecord.error` populated.

    Implementing a custom strategy (e.g. one that uses ``aiohttp``) requires
    only subclassing this class and implementing :meth:`check`.
    """

    @abstractmethod
    def check(self, record: LinkRecord) -> LinkRecord:
        """Resolve the HTTP status for *record*.

        :param record: An unresolved link record (``status=None``).
        :type record: LinkRecord
        :returns: A new :class:`~pdf_link_checker.models.LinkRecord` with
            ``status`` and ``error`` populated.
        :rtype: LinkRecord
        """


class RequestsLinkChecker(LinkCheckerStrategy):
    """Link checker that performs HTTP GET requests via the ``requests`` library.

    Strips leading/trailing whitespace from URIs before requesting (some PDF
    generators embed URIs with surrounding spaces). Follows redirects and
    records the final HTTP status code.

    :param timeout: Seconds to wait before considering a request timed out.
        Defaults to ``5.0``.
    :type timeout: float
    :param session: An optional pre-configured :class:`requests.Session`.
        When ``None`` a new session is created internally. Providing a
        session allows callers to configure headers, proxies, or retry
        adapters.
    :type session: requests.Session or None

    Example::

        checker = RequestsLinkChecker(timeout=10)
        resolved = checker.check(LinkRecord(page=1, uri="https://example.com",
                                            status=None))
        print(resolved.status)  # e.g. 200
    """

    def __init__(
        self,
        timeout: float = 5.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        """Initialise the checker.

        :param timeout: Request timeout in seconds. Defaults to ``5.0``.
        :param session: Optional :class:`requests.Session` to reuse across
            requests. A new session is created when ``None``.
        """
        self.timeout = timeout
        self._session = session or requests.Session()

    def check(self, record: LinkRecord) -> LinkRecord:
        """Perform an HTTP GET for *record.uri* and return a resolved record.

        :param record: An unresolved link record.
        :type record: LinkRecord
        :returns: A new :class:`~pdf_link_checker.models.LinkRecord` with
            ``status`` and ``error`` set.
        :rtype: LinkRecord
        """
        uri = record.uri.strip()
        try:
            response = self._session.get(
                uri,
                timeout=self.timeout,
                stream=True,
                allow_redirects=True,
            )
            status = response.status_code
            response.close()
            error = "NA"
            logger.info("Page %4d | %s -> %s", record.page, uri, status)

        except requests.exceptions.Timeout as exc:
            status = None
            error = f"Timeout: {exc}"
            logger.warning("Page %4d | %s -> TIMEOUT", record.page, uri)

        except requests.exceptions.ConnectionError as exc:
            status = None
            error = f"ConnectionError: {exc}"
            logger.warning("Page %4d | %s -> CONNECTION ERROR", record.page, uri)

        except requests.exceptions.RequestException as exc:
            status = None
            error = f"RequestException: {exc}"
            logger.warning(
                "Page %4d | %s -> REQUEST ERROR: %s", record.page, uri, exc
            )

        return LinkRecord(
            page=record.page,
            uri=record.uri,
            status=status,
            error=error,
        )


class ConcurrentLinkChecker:
    """Orchestrates concurrent link checking using a pluggable strategy.

    Uses :class:`concurrent.futures.ThreadPoolExecutor` to parallelise HTTP
    requests. Each worker receives its own :class:`LinkRecord` and returns a
    new resolved record — there is no shared mutable state between threads.
    An optional *progress_callback* is invoked on the main thread after each
    result becomes available (Observer pattern).

    :param strategy: The underlying :class:`LinkCheckerStrategy` to use for
        each individual link.
    :type strategy: LinkCheckerStrategy
    :param max_workers: Maximum number of concurrent worker threads.
        Defaults to ``4``.
    :type max_workers: int
    :param progress_callback: Optional callable invoked with each resolved
        :class:`~pdf_link_checker.models.LinkRecord` as it completes.
    :type progress_callback: Callable[[LinkRecord], None] or None

    Example::

        checker = ConcurrentLinkChecker(
            strategy=RequestsLinkChecker(timeout=10),
            max_workers=8,
        )
        resolved = checker.check_all(records)
    """

    def __init__(
        self,
        strategy: LinkCheckerStrategy,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[LinkRecord], None]] = None,
    ) -> None:
        """Initialise the concurrent checker.

        :param strategy: Link checking strategy to use per record.
        :param max_workers: Thread pool size. Defaults to ``4``.
        :param progress_callback: Optional per-result callback.
        """
        self.strategy = strategy
        self.max_workers = max_workers
        self.progress_callback = progress_callback

    def check_all(self, records: List[LinkRecord]) -> List[LinkRecord]:
        """Check all *records* concurrently and return results sorted by page.

        Submits every record to the thread pool independently, collects
        resolved records as futures complete, fires the progress callback if
        set, then sorts the final list by page number.

        :param records: Unresolved link records (``status=None``).
        :type records: List[LinkRecord]
        :returns: Resolved records sorted ascending by page number.
        :rtype: List[LinkRecord]
        """
        if not records:
            logger.info("No records to check.")
            return []

        resolved: List[LinkRecord] = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            future_map = {
                executor.submit(self.strategy.check, record): record
                for record in records
            }
            for future in concurrent.futures.as_completed(future_map):
                result = future.result()
                resolved.append(result)
                if self.progress_callback:
                    self.progress_callback(result)

        resolved.sort(key=lambda r: (r.page, r.uri))
        return resolved
