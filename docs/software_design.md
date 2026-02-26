# Software Design

## Overview

PDF Link Checker v2.0 is structured as a proper Python package (`pdf_link_checker`)
organised around three well-known Gang-of-Four design patterns: **Strategy**,
**Factory**, and **Observer**. The architecture separates concerns cleanly into
four layers, each with a single responsibility, making the system easy to test,
extend, and maintain.

```
pdf_link_checker/
├── models.py      ← Data Transfer Object (DTO)
├── extractor.py   ← Strategy: PDF link extraction
├── checker.py     ← Strategy + Observer: HTTP status checking
├── reporter.py    ← Strategy + Factory: report serialisation
└── cli.py         ← Pipeline orchestration + CLI entry point
```

---

## Design Patterns

### 1. Strategy Pattern

The **Strategy** pattern defines a family of algorithms, encapsulates each one,
and makes them interchangeable. It lets the algorithm vary independently from
the clients that use it.

Three Strategy hierarchies are used:

#### PDF Extraction Strategy (`extractor.py`)

```
PDFExtractorStrategy (ABC)
    └── PyPDFExtractor          ← uses pypdf 4.x
         (future: MuPDFExtractor, PdfiumExtractor, …)
```

`PyPDFExtractor` can be swapped for another backend (e.g. `pdfplumber`,
`pymupdf`) without touching any other layer of the application. The only
contract is `extract_links(pdf_path: Path) -> List[LinkRecord]`.

#### Link Checker Strategy (`checker.py`)

```
LinkCheckerStrategy (ABC)
    └── RequestsLinkChecker     ← uses requests library
         (future: AiohttpChecker, HeadOnlyChecker, …)
```

`ConcurrentLinkChecker` is a separate orchestration class that wraps any
`LinkCheckerStrategy` and parallelises it with `concurrent.futures`.

#### Report Writer Strategy (`reporter.py`)

```
ReportWriterStrategy (ABC)
    ├── CSVReportWriter
    └── JSONReportWriter
         (future: HTMLReportWriter, ExcelReportWriter, …)
```

---

### 2. Factory Pattern

`ReportWriterFactory.create(output_path)` selects and instantiates the correct
`ReportWriterStrategy` based solely on the file extension of `output_path`.
This shields the calling code (`cli.py`) from knowing which concrete writer
class to instantiate, and makes adding a new format a one-line registry change.

```python
# Adding a new format requires only:
ReportWriterFactory._registry[".xlsx"] = ExcelReportWriter
```

---

### 3. Observer Pattern (Progress Callback)

`ConcurrentLinkChecker` accepts an optional `progress_callback` — a callable
invoked each time a future completes. This is a lightweight implementation of
the Observer pattern: the checker (subject) notifies any interested observer
(the callback) without coupling to a specific output mechanism. The CLI passes
a `print`-based callback; tests can pass a list-appender to assert call counts.

---

## Module Descriptions

### `models.py` — Data Transfer Object

`LinkRecord` is a Python `dataclass` that carries the result of one link check
between all layers. It is immutable in practice and has no behaviour beyond the
`as_row()` helper used by `CSVReportWriter`.

| Field    | Type          | Description                              |
|----------|---------------|------------------------------------------|
| `page`   | `int`         | 1-based PDF page number                  |
| `uri`    | `str`         | Raw URI from the PDF annotation          |
| `status` | `int \| None` | HTTP status code, or `None` on failure   |
| `error`  | `str`         | Error description, or `'NA'` on success  |

---

### `extractor.py` — PDF Link Extraction

`PyPDFExtractor` iterates all pages of a `pypdf.PdfReader`, inspects each
annotation for a URI action (`/A` → `/URI`), and collects one `LinkRecord`
per discovered hyperlink with `status=None`.

**Key design decisions:**

- Uses `pathlib.Path` throughout for cross-platform path handling.
- Indirect annotation objects are dereferenced with `.get_object()`.
- A missing `/Annots` key is silently skipped (not all pages have links).
- `status` is deliberately left as `None` to maintain single-responsibility
  separation between extraction and checking.

---

### `checker.py` — HTTP Status Resolution

`RequestsLinkChecker` performs HTTP GET requests using a `requests.Session`.
URI strings are stripped of whitespace before use. Redirects are followed
(`allow_redirects=True`) and the final status code is recorded.

`ConcurrentLinkChecker` wraps any `LinkCheckerStrategy` and submits each
`LinkRecord` as an independent task to a `ThreadPoolExecutor`. Because each
worker receives its own input record and returns a new `LinkRecord`, there is
**no shared mutable state** between threads. Results are gathered via
`concurrent.futures.as_completed`, then sorted by page number.

This approach eliminates the thread-safety bug present in v1 (unsynchronised
`list.append` across threads) and the off-by-one error in `get_split`.

---

### `reporter.py` — Report Serialisation

`CSVReportWriter` writes a UTF-8 CSV with a fixed header row. Python's `csv`
module handles line endings, ensuring Windows (CRLF) and POSIX (LF) behaviour
is correct on each platform.

`JSONReportWriter` writes a JSON array where `None` status values serialise
naturally as JSON `null`.

`ReportWriterFactory` maps file extensions to writer classes. Any missing
parent directories are created automatically (`mkdir(parents=True, exist_ok=True)`).

---

### `cli.py` — Pipeline Orchestration

`run()` is the top-level pipeline function. It is decoupled from argument
parsing so it can be called programmatically (e.g. from tests or scripts)
without invoking `sys.argv`. `main()` wraps `run()` with `argparse` and
maps system-exit codes to semantic meanings.

```
main()
  └─ run()
       ├─ PyPDFExtractor.extract_links()
       ├─ ConcurrentLinkChecker.check_all()
       │    └─ RequestsLinkChecker.check()  ×N  (threaded)
       └─ ReportWriterFactory.create().write()
```

---

## Data Flow

```
 PDF file
    │
    ▼
PyPDFExtractor.extract_links()
    │  returns List[LinkRecord(status=None)]
    ▼
ConcurrentLinkChecker.check_all()
    │  ThreadPoolExecutor submits one future per record
    │  returns List[LinkRecord(status=int|None)]  sorted by page
    ▼
ReportWriterFactory.create(output_path)
    │  selects CSVReportWriter or JSONReportWriter
    ▼
writer.write(records, output_path)
    │
    ▼
 Report file (.csv or .json)
```

---

## Cross-Platform Compatibility

All file paths use `pathlib.Path` — no hardcoded path separators. CSV output
uses Python's built-in `csv` module with `newline=""` to delegate line-ending
choice to the platform. The `requests` library handles SSL certificates via
`certifi`, which is bundled correctly on all three platforms.

---

## Extension Points

| What to extend        | How                                                      |
|-----------------------|----------------------------------------------------------|
| New PDF backend       | Subclass `PDFExtractorStrategy`, implement `extract_links` |
| New HTTP strategy     | Subclass `LinkCheckerStrategy`, implement `check`        |
| New output format     | Subclass `ReportWriterStrategy`, register in `ReportWriterFactory._registry` |
| Progress reporting    | Pass a custom `progress_callback` to `ConcurrentLinkChecker` |

---

## Dependency Versions

| Package   | Version  | Purpose                        |
|-----------|----------|--------------------------------|
| `pypdf`   | `>=4.0`  | PDF parsing (replaces PyPDF2)  |
| `requests`| `>=2.31` | HTTP link checking             |
