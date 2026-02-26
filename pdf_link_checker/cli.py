"""
Command-line interface for PDF Link Checker.

Provides the ``pdf-link-checker`` entry point. The :func:`run` function
implements the core pipeline and can be called programmatically; :func:`main`
wraps it with CLI argument parsing and logging setup.
"""

import argparse
import logging
import pathlib
import sys
from typing import List

from .checker import ConcurrentLinkChecker, RequestsLinkChecker
from .extractor import PyPDFExtractor
from .models import LinkRecord
from .reporter import ReportWriterFactory

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    """Configure the root logger for console output.

    :param verbose: When ``True`` the log level is set to ``DEBUG``;
        otherwise ``INFO``.
    :type verbose: bool
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _build_progress_callback() -> callable:
    """Return a progress callback that prints one line per resolved link.

    :returns: A callable ``(LinkRecord) -> None``.
    :rtype: callable
    """

    def _callback(record: LinkRecord) -> None:
        status_display = str(record.status) if record.status is not None else "ERR"
        print(f"  Page {record.page:>4} | {status_display:<5} | {record.uri}")

    return _callback


def build_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    Exposed as a public function so callers can extend or test the parser
    independently.

    :returns: Configured :class:`argparse.ArgumentParser`.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="pdf-link-checker",
        description=(
            "Extract and validate all hyperlinks in a PDF file, "
            "producing a status report in CSV or JSON format."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "pdf",
        type=pathlib.Path,
        help="Path to the PDF file to analyse.",
    )
    parser.add_argument(
        "output",
        type=pathlib.Path,
        help="Output report file path (.csv or .json).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        metavar="SECONDS",
        help="HTTP request timeout in seconds.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        metavar="N",
        help="Number of concurrent worker threads.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug-level logging.",
    )
    return parser


def run(
    pdf: pathlib.Path,
    output: pathlib.Path,
    timeout: float = 5.0,
    workers: int = 4,
    progress_callback: callable = None,
) -> List[LinkRecord]:
    """Orchestrate PDF extraction, concurrent link checking, and report writing.

    This is the core pipeline function. It is intentionally decoupled from
    argument parsing so it can be called programmatically or from tests.

    :param pdf: Path to the input PDF file.
    :type pdf: pathlib.Path
    :param output: Destination report file path (``.csv`` or ``.json``).
    :type output: pathlib.Path
    :param timeout: HTTP request timeout in seconds. Defaults to ``5.0``.
    :type timeout: float
    :param workers: Number of concurrent worker threads. Defaults to ``4``.
    :type workers: int
    :param progress_callback: Optional callable invoked after each link is
        checked. Receives the resolved
        :class:`~pdf_link_checker.models.LinkRecord`. Defaults to ``None``.
    :type progress_callback: callable or None
    :returns: All resolved :class:`~pdf_link_checker.models.LinkRecord`
        objects, sorted by page number.
    :rtype: List[LinkRecord]
    :raises FileNotFoundError: If *pdf* does not exist.
    :raises ValueError: If the output format is not supported.
    """
    logger.info("=== PDF Link Checker ===")
    logger.info("Input:   %s", pdf)
    logger.info("Output:  %s", output)
    logger.info("Timeout: %.1f s  Workers: %d", timeout, workers)

    extractor = PyPDFExtractor()
    records = extractor.extract_links(pdf)

    if not records:
        logger.warning("No hyperlinks found in PDF — nothing to check.")
        writer = ReportWriterFactory.create(output)
        writer.write([], output)
        return []

    logger.info("Checking %d link(s) …", len(records))
    checker = ConcurrentLinkChecker(
        strategy=RequestsLinkChecker(timeout=timeout),
        max_workers=workers,
        progress_callback=progress_callback,
    )
    resolved = checker.check_all(records)

    writer = ReportWriterFactory.create(output)
    writer.write(resolved, output)

    broken = [r for r in resolved if r.status is None or r.status >= 400]
    logger.info(
        "Checked %d link(s): %d OK, %d broken/unreachable.",
        len(resolved),
        len(resolved) - len(broken),
        len(broken),
    )
    return resolved


def main() -> None:
    """Entry point for the ``pdf-link-checker`` command.

    Parses CLI arguments, configures logging, and delegates to :func:`run`.
    Exits with code ``1`` on fatal errors and ``130`` on keyboard interrupt.
    """
    parser = build_arg_parser()
    args = parser.parse_args()
    _configure_logging(args.verbose)

    try:
        resolved = run(
            pdf=args.pdf,
            output=args.output,
            timeout=args.timeout,
            workers=args.workers,
            progress_callback=_build_progress_callback(),
        )
        broken = [r for r in resolved if r.status is None or r.status >= 400]
        print(
            f"\nDone. Checked {len(resolved)} link(s) — "
            f"{len(broken)} broken/unreachable. "
            f"Report saved to: {args.output}"
        )
    except FileNotFoundError as exc:
        logger.error("PDF not found: %s", exc)
        sys.exit(1)
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
