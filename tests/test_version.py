"""The package version tracks the dataset version, in three places at once.

``gasbrinebench.__version__`` is only useful if it names the snapshot of the
database a result was computed from. These assertions are what keep it honest:
if someone bumps ``CITATION.cff`` for a release and forgets the package, CI
fails here rather than a year later in somebody's methods section.
"""

from __future__ import annotations

import re

import gasbrinebench as gbb


def _cff_version(repo_root) -> str | None:
    for line in (repo_root / "CITATION.cff").read_text().splitlines():
        m = re.match(r"^version:\s*[\"']?([^\"'\s]+)[\"']?\s*$", line)
        if m:
            return m.group(1)
    return None


def test_version_is_a_nonempty_string():
    assert isinstance(gbb.__version__, str)
    assert gbb.__version__


def test_version_matches_citation_cff(repo_root):
    cff = _cff_version(repo_root)
    assert cff is not None, "CITATION.cff has no version: field"
    assert cff == gbb.__version__


def test_version_appears_in_the_changelog(repo_root):
    text = (repo_root / "CHANGELOG.md").read_text()
    assert gbb.__version__ in text


def test_module_docstring_example_matches(repo_root):
    """The package docstring shows the version; that is a fourth place to drift.

    It is a doctest, so it does fail on release -- but it fails as an opaque
    expected/got diff in a doctest run, which is not where someone bumping a
    version is looking. Holding it here means the version test names it.
    """
    doc = gbb.__doc__ or ""
    shown = re.findall(r">>> gbb\.__version__\n'([^']+)'", doc)
    assert shown, "the package docstring no longer shows gbb.__version__"
    assert shown == [gbb.__version__], (
        f"package docstring shows {shown} but __version__ is "
        f"{gbb.__version__!r}; update the doctest in gasbrinebench/__init__.py"
    )


def test_cli_reports_the_same_version(capsys):
    import pytest

    from gasbrinebench.__main__ import main

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == gbb.__version__
