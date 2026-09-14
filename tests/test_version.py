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


def test_cli_reports_the_same_version(capsys):
    import pytest

    from gasbrinebench.__main__ import main

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == gbb.__version__
