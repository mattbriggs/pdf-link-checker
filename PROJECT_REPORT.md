# Project Report — PDF Link Checker v2.0.0

**Date:** 2026-02-25
**Branch:** `refactor/design-patterns`
**Python:** 3.12.7
**pytest:** 9.0.2

---

## Executive Summary

The PDF Link Checker has been fully refactored from a single-file script (v1.1.1)
into a well-structured, cross-platform Python package (v2.0.0). The refactor
addresses every code-quality issue identified in the v1 review: deprecated
library usage, thread-unsafe state sharing, off-by-one page-splitting logic,
hardcoded Windows paths, and live network calls in tests.

**All 106 tests pass. Coverage is 99.5%.**

---

## Test Results

```
============================= test session starts ==============================
platform darwin -- Python 3.12.7, pytest-9.0.2

collected 106 items

tests/integration/test_pipeline.py   13 passed
tests/unit/test_checker.py           24 passed
tests/unit/test_cli.py               21 passed
tests/unit/test_extractor.py         17 passed
tests/unit/test_models.py            12 passed
tests/unit/test_reporter.py          19 passed

============================== 106 passed in 15.37s ==============================
```

---

## Coverage Report

```
Name                            Stmts   Miss  Cover   Missing
-------------------------------------------------------------
pdf_link_checker/__init__.py        7      0   100%
pdf_link_checker/checker.py        54      0   100%
pdf_link_checker/cli.py            65      1    98%   203
pdf_link_checker/extractor.py      42      0   100%
pdf_link_checker/models.py         10      0   100%
pdf_link_checker/reporter.py       38      0   100%
-------------------------------------------------------------
TOTAL                             216      1    99%   Overall: 99.54%
```

The single uncovered line (cli.py:203) is the `if __name__ == "__main__"` guard,
which is standard practice to exclude from coverage as it cannot be meaningfully
tested by the test runner without spawning a subprocess.

---

## What Changed

### Architecture

| Aspect | v1 (legacy) | v2 (refactored) |
|--------|-------------|-----------------|
| Structure | Single script `pdf_link_check.py` | Package `pdf_link_checker/` with 5 modules |
| Design Patterns | None | Strategy, Factory, Observer |
| PDF library | `PyPDF2==1.27.9` (unmaintained) | `pypdf>=4.0` (actively maintained) |
| Concurrency | `threading.Thread` with shared mutable list | `concurrent.futures.ThreadPoolExecutor`, no shared state |
| Path handling | Hardcoded `\\` separators (Windows-only) | `pathlib.Path` throughout (cross-platform) |
| CLI | `input()` prompts | `argparse` with `--timeout`, `--workers`, `--verbose` |
| Output formats | CSV only | CSV and JSON via Factory + Strategy |
| Logging | `print()` only | `logging` module with configurable levels |
| Docstrings | None | Sphinx-compatible throughout |
| Type hints | None | Full type annotations |

### Bugs Fixed

| Bug | v1 | v2 |
|-----|----|----|
| Thread-unsafe list.append across threads | Unguarded `list.append()` in worker threads | Each worker returns a new `LinkRecord`; no shared state |
| Off-by-one in `get_split` | Pages 25, 50, 75 potentially skipped | `get_split` eliminated; all links checked individually |
| File handle leak in `main()` | `open()` without `with` statement | `with open(…) as f:` used everywhere |
| Deprecated PyPDF2 API | `PdfFileReader`, `getPage()`, `numPages` | `PdfReader`, `reader.pages[i]`, `len(reader.pages)` |
| Windows-only test paths | `data\\testpdf.pdf` | `pathlib.Path` in all fixtures |
| Live network calls in tests | Tests hit real URLs | All HTTP calls mocked via `unittest.mock` |

---

## Module Summary

| Module | Lines | Coverage | Responsibility |
|--------|-------|----------|----------------|
| `models.py` | 10 | 100% | `LinkRecord` DTO |
| `extractor.py` | 42 | 100% | PDF link extraction (Strategy) |
| `checker.py` | 54 | 100% | HTTP checking (Strategy + Observer) |
| `reporter.py` | 38 | 100% | Report serialisation (Strategy + Factory) |
| `cli.py` | 65 | 98% | Pipeline orchestration + CLI |
| `__init__.py` | 7 | 100% | Public API exports |
| **Total** | **216** | **99.5%** | |

---

## Test Suite Summary

| Suite | Tests | Description |
|-------|-------|-------------|
| `tests/unit/test_models.py` | 12 | `LinkRecord` construction and `as_row()` |
| `tests/unit/test_extractor.py` | 17 | PDF extraction, error handling, mocked pypdf |
| `tests/unit/test_checker.py` | 24 | HTTP checking, error types, concurrency |
| `tests/unit/test_reporter.py` | 19 | CSV/JSON writers, factory, edge cases |
| `tests/unit/test_cli.py` | 21 | Parser, logging config, callback, `main()` exit codes |
| `tests/integration/test_pipeline.py` | 13 | Full pipeline with real PDFs + mocked HTTP |
| **Total** | **106** | All passing |

---

## Design Patterns Applied

### Strategy Pattern
Three independent strategy hierarchies allow swapping backends without
touching the rest of the codebase:
- `PDFExtractorStrategy` → `PyPDFExtractor`
- `LinkCheckerStrategy` → `RequestsLinkChecker`
- `ReportWriterStrategy` → `CSVReportWriter`, `JSONReportWriter`

### Factory Pattern
`ReportWriterFactory.create(output_path)` selects the correct writer from a
registry keyed on file extension. Adding a new format requires one line.

### Observer Pattern (Progress Callback)
`ConcurrentLinkChecker` accepts an optional `progress_callback` callable.
The CLI passes a printing callback; tests pass a list-appender. The checker
is decoupled from output concerns.

---

## Remaining Recommendations

1. **Add `HEAD`-first checking** — An optional `HeadOnlyChecker` strategy
   that sends HTTP HEAD before GET would reduce bandwidth for large PDFs.

2. **Async support** — An `AiohttpChecker` strategy using `asyncio` would
   eliminate thread-pool overhead for very large link counts.

3. **Retry logic** — A `requests.adapters.HTTPAdapter` with retry semantics
   could be injected into `RequestsLinkChecker` to reduce false negatives
   from transient network errors.

4. **mkdocs API reference** — Adding `mkdocstrings` would auto-generate an
   API reference page from the Sphinx-compatible docstrings.

5. **GitHub Actions CI** — A `.github/workflows/ci.yml` running
   `pytest --cov` on push would enforce the coverage threshold continuously.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pypdf` | `>=4.0` (installed: 6.7.3) | PDF parsing |
| `requests` | `>=2.31` | HTTP checking |
| `pytest` | `>=7.4` (installed: 9.0.2) | Test runner |
| `pytest-cov` | `>=4.1` (installed: 7.0.0) | Coverage |
| `pytest-mock` | `>=3.11` (installed: 3.15.1) | Mock utilities |
