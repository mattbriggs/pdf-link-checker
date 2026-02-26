# PDF Link Checker

**PDF Link Checker** is a cross-platform command-line tool that extracts every
hyperlink from a PDF document and verifies its HTTP status, producing a report
in CSV or JSON format.

Release: **V2.0.0**

---

## Features

- Extracts annotated hyperlinks from any PDF using the maintained `pypdf` library
- Checks each link concurrently via a configurable thread pool
- Reports in CSV or JSON — selected automatically by file extension
- Cross-platform: macOS, Linux, and Windows
- Structured with Software Design Patterns (Strategy, Factory, Observer)
- Full test suite: unit tests per module + integration tests (pytest)

---

## Requirements

- Python 3.9 or later
- `pypdf >= 4.0`
- `requests >= 2.31`

---

## Installation

### From source (recommended for development)

```bash
git clone https://github.com/mattbriggs/pdf-link-checker.git
cd pdf-link-checker
pip install -e ".[dev]"
```

### Dependencies only

```bash
pip install pypdf requests
```

---

## Usage

### Command line

```bash
pdf-link-checker <PDF> <OUTPUT>
```

**Positional arguments**

| Argument  | Description                                    |
|-----------|------------------------------------------------|
| `PDF`     | Path to the PDF file to analyse                |
| `OUTPUT`  | Output report path (`.csv` or `.json`)         |

**Optional arguments**

| Flag               | Default | Description                             |
|--------------------|---------|-----------------------------------------|
| `--timeout SECS`   | `5.0`   | HTTP request timeout in seconds         |
| `--workers N`      | `4`     | Number of concurrent worker threads     |
| `--verbose` / `-v` | off     | Enable debug-level logging              |

**Examples**

```bash
# Basic CSV report
pdf-link-checker document.pdf report.csv

# JSON report with a 10-second timeout and 8 threads
pdf-link-checker document.pdf report.json --timeout 10 --workers 8

# Verbose output for debugging
pdf-link-checker document.pdf report.csv --verbose
```

### Programmatic API

```python
import pathlib
from pdf_link_checker.cli import run

resolved = run(
    pdf=pathlib.Path("document.pdf"),
    output=pathlib.Path("report.csv"),
    timeout=10.0,
    workers=8,
)

broken = [r for r in resolved if r.status is None or r.status >= 400]
print(f"{len(broken)} broken link(s) found.")
```

---

## Output Format

### CSV

```
page,uri,status,request-error
1,https://example.com,200,NA
2,https://old.example.com/missing,404,NA
3,https://unreachable.example.com,NA,"Timeout: ..."
```

### JSON

```json
[
  {"page": 1, "uri": "https://example.com", "status": 200, "error": "NA"},
  {"page": 2, "uri": "https://old.example.com/missing", "status": 404, "error": "NA"},
  {"page": 3, "uri": "https://unreachable.example.com", "status": null, "error": "Timeout: ..."}
]
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=pdf_link_checker --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=pdf_link_checker --cov-report=html
# then open htmlcov/index.html
```

---

## Project Structure

```
pdf-link-checker/
├── pdf_link_checker/          # Main package
│   ├── __init__.py
│   ├── models.py              # LinkRecord data class (DTO)
│   ├── extractor.py           # PDF link extraction (Strategy)
│   ├── checker.py             # HTTP checking (Strategy + Observer)
│   ├── reporter.py            # Report writing (Strategy + Factory)
│   └── cli.py                 # CLI entry point + run() pipeline
├── tests/
│   ├── conftest.py            # Shared fixtures (data paths)
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_extractor.py
│   │   ├── test_checker.py
│   │   ├── test_reporter.py
│   │   └── test_cli.py
│   └── integration/
│       └── test_pipeline.py
├── docs/
│   ├── index.md               # MkDocs home page
│   └── software_design.md     # Architecture and design patterns
├── data/                      # Test PDFs
├── pyproject.toml
├── mkdocs.yml
└── README.md
```

---

## Building the Documentation

Documentation is built with [MkDocs](https://www.mkdocs.org/) and the
[Material theme](https://squidfunk.github.io/mkdocs-material/).

```bash
pip install -e ".[docs]"
mkdocs serve          # live preview at http://127.0.0.1:8000
mkdocs build          # static site in site/
```

---

## Architecture

See [docs/software_design.md](docs/software_design.md) for a full description
of the design patterns used (Strategy, Factory, Observer), module
responsibilities, and extension points.

---

## License

MIT — see [LICENSE](LICENSE).
