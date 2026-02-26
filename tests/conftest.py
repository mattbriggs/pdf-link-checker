"""
Shared pytest fixtures for the pdf_link_checker test suite.

Fixtures defined here are available to all test modules without explicit
import. The ``data_dir`` fixture resolves the path to the ``data/``
folder at the repository root, ensuring cross-platform compatibility.
"""

import pathlib
import pytest

# Resolve data/ relative to this conftest, regardless of working directory.
_REPO_ROOT = pathlib.Path(__file__).parent.parent
DATA_DIR = _REPO_ROOT / "data"


@pytest.fixture(scope="session")
def data_dir() -> pathlib.Path:
    """Return the absolute path to the repository's ``data/`` directory.

    :returns: Path to ``data/``.
    :rtype: pathlib.Path
    """
    return DATA_DIR


@pytest.fixture(scope="session")
def pdf_short(data_dir: pathlib.Path) -> pathlib.Path:
    """Return the path to the short test PDF (fewer than 13 pages).

    :param data_dir: Injected ``data_dir`` fixture.
    :returns: Path to ``data/pdflink.pdf``.
    :rtype: pathlib.Path
    """
    return data_dir / "pdflink.pdf"


@pytest.fixture(scope="session")
def pdf_long(data_dir: pathlib.Path) -> pathlib.Path:
    """Return the path to the longer test PDF (more than 13 pages).

    :param data_dir: Injected ``data_dir`` fixture.
    :returns: Path to ``data/testpdf.pdf``.
    :rtype: pathlib.Path
    """
    return data_dir / "testpdf.pdf"
