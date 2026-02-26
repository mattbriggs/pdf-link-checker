# PDF Link Checker

**PDF Link Checker** is a cross-platform command-line tool that extracts every
hyperlink from a PDF document and checks its HTTP status, producing a report in
CSV or JSON format.

## Features

- Extracts all annotated hyperlinks from any PDF using the `pypdf` library
- Checks each link concurrently using a configurable thread pool
- Produces CSV or JSON reports
- Cross-platform: macOS, Linux, and Windows
- Structured with Software Design Patterns for extensibility
- Full test suite with unit and integration tests

## Quick Start

### Install

```bash
pip install -e ".[dev]"
```

### Run

```bash
pdf-link-checker document.pdf report.csv
```

With options:

```bash
pdf-link-checker document.pdf report.json --timeout 10 --workers 8 --verbose
```

## Output Formats

| Extension | Format |
|-----------|--------|
| `.csv`    | Comma-separated values with header row |
| `.json`   | JSON array of link objects |

Each record contains:

| Field           | Description |
|-----------------|-------------|
| `page`          | 1-based page number where the link appears |
| `uri`           | The raw URI extracted from the PDF |
| `status`        | HTTP status code, or `NA` if the request failed |
| `request-error` | Error description, or `NA` if successful |

## Navigation

- [Software Design](software_design.md) — Architecture, design patterns, and module descriptions
