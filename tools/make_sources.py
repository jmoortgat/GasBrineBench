#!/usr/bin/env python3
"""Generate SOURCES.md (and SOURCES.bib) from the benchmark CSVs.

THE POINT OF THE MANIFEST
-------------------------
Every number in this benchmark was measured by someone else and published in
the primary literature. We hold the papers locally to transcribe them; we
cannot and will not redistribute them. The manifest closes that gap: for each
source it records the full bibliographic reference, a DOI, a resolvable URL,
and exactly which rows of the benchmark came from it. Anyone can therefore
walk the manifest, obtain each paper through their own library, and rebuild
the database from primary sources -- without us passing on a single
copyrighted page.

WHY IT IS GENERATED AND NOT WRITTEN BY HAND
-------------------------------------------
A hand-maintained source list drifts the moment a dataset is added. This
script reads the CSVs themselves, so the coverage numbers, ranges, and
quality-code mixes in SOURCES.md are always what the data actually says.
Re-run it after any change to the data and commit the diff.

INPUTS AND OUTPUTS (all inside this repository)
-----------------------------------------------
    data/*.csv          the benchmark itself
    bib/references.bib  the hand-maintained bibliographic library
      ->  SOURCES.md    the manifest
      ->  SOURCES.bib   the subset of records the data actually cites

Nothing outside the repository is read, so a fresh clone regenerates both
outputs byte for byte. `SOURCES.bib` is never read back as an input: it is the
output, and a stale harvested copy must not be able to outrank the library.

WHAT IT WILL NOT DO
-------------------
It never invents a reference. A source key with no bibliographic record in any
of the .bib files it was given is reported, by name, in a "needs citation"
section. A record that is itself marked as a placeholder is reported in a
"placeholder citation" section. Neither is quietly filled in.

It does carry one small table of hand-checked corrections, SOURCE_KEY_FIXES,
for raw `source` cells that demonstrably do not name the paper the rows came
from -- a misspelt or truncated surname, a missing year, a year belonging to a
thesis rather than to the published article. Every one of those was settled by
reading the primary paper and checking the rows' own T, P, salt and composition
grid against its tables, and every one is printed with its evidence in a
"Source-key corrections" section so it can be audited. A defect that could not
be settled that way is left alone and stays in "needs citation".

USAGE
-----
    python3 tools/make_sources.py                       # write SOURCES.md + SOURCES.bib
    python3 tools/make_sources.py --data-dir PATH
    python3 tools/make_sources.py --bib A.bib --bib B.bib
    python3 tools/make_sources.py --stdout               # print, write nothing
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Both inputs live inside this repository: the manifest regenerates from a
# clone alone, with nothing outside it on the path. `bib/references.bib` is the
# hand-maintained bibliographic library; `SOURCES.bib` at the root is this
# script's OUTPUT and is deliberately not read back (see main()).
DEFAULT_DATA_DIR = os.path.join(HERE, "data")
DEFAULT_BIBS = [
    os.path.join(HERE, "bib", "references.bib"),
]

# Superseded intermediates that must not be counted twice.
SKIP_CSV_SUFFIXES = ("_pre_quality.csv",)

MOLALITY_COLS = ["m_Na", "m_Cl", "m_K", "m_Ca", "m_Mg", "m_SO4"]
ION_LABEL = {"m_Na": "Na+", "m_Cl": "Cl-", "m_K": "K+",
             "m_Ca": "Ca2+", "m_Mg": "Mg2+", "m_SO4": "SO4 2-"}
SALT_BY_IONSET = {
    frozenset(["m_Na", "m_Cl"]): "NaCl",
    frozenset(["m_K", "m_Cl"]): "KCl",
    frozenset(["m_Ca", "m_Cl"]): "CaCl2",
    frozenset(["m_Mg", "m_Cl"]): "MgCl2",
    frozenset(["m_Na", "m_SO4"]): "Na2SO4",
    frozenset(["m_K", "m_SO4"]): "K2SO4",
    frozenset(["m_Mg", "m_SO4"]): "MgSO4",
    frozenset(["m_Ca", "m_SO4"]): "CaSO4",
}

PLACEHOLDER_RE = re.compile(r"placeholder|to be confirmed|TODO|FIXME", re.I)


# --------------------------------------------------------------------------
# source-key normalisation
# --------------------------------------------------------------------------

# A raw `source` value is one of several historical spellings of the same
# citation. These all have to collapse onto one identity:
#
#   TEYMOURI(2017)                        TEYMOURI_2017
#   KOSCHEL(2006)                         Koschel2006_FPE247_T4_T7
#   Chabab2021_JCED66_T2                  Chabab2021_JCED66_T3_tech1
#   ALGHAFRI(2012) / EXP_NaCl_T298K.txt   (x34 isotherm files)
#
# while these must stay apart, because they are different papers:
#
#   ZHAO(2015)   ZHAOb(2015)   ZHAOc_2015
#   HOU(2013b)   Hou2013_JSCF78_T2
#
# So: drop the trailing file/table/figure locator, keep any disambiguating
# letter suffix, and normalise punctuation and case. Nothing that could be a
# suffix is ever discarded.

_YEAR_RE = re.compile(r"(?P<name>[A-Za-z][A-Za-z'\- ]*)"
                      r"[\s_(]*"
                      r"(?P<year>1[89]\d{2}|20\d{2})"
                      r"(?P<post>[a-z]{1,3})?")


# --------------------------------------------------------------------------
# demonstrably defective raw `source` values
# --------------------------------------------------------------------------
#
# A handful of raw `source` cells do not name the paper the rows were
# transcribed from: a surname is misspelt or truncated, a year is missing, or
# the year belongs to a thesis/preprint rather than to the published article
# the numbers were read out of. Left alone they either resolve to nothing or,
# worse, look ambiguous between two real papers by the same author.
#
# These are NOT normalisation rules and NOT guesses. Each entry was settled by
# reading the primary PDF held locally and checking the rows' own temperature,
# pressure, salt and composition grid against the paper's tables; the evidence
# is reproduced verbatim in the "Source-key corrections" section of SOURCES.md
# so a reader can audit every one of them. A defect that could not be settled
# this way is deliberately absent here and stays in "Needs citation" instead.
#
# The corrections live here rather than in the CSVs because the CSVs are
# themselves generated -- their `source` column is copied from upstream
# Multi_Salt curation artefacts -- so an edit applied to the CSV would be
# silently undone by the next rebuild, and two of the raw strings are asserted
# verbatim by the benchmark's own test suite.

# Shared by the two Hou brine tables, which are the same defect twice.
_HOU_JSCF78 = (
    "the key names the volume and then resolves to the wrong paper. "
    "`JSCF78` is J. Supercrit. Fluids volume 78, which is Hou, Maitland & "
    "Trusler's *brine* paper (Hou2013b); volume 73 is the same group's "
    "CO2 + H2O binary (Hou2013), and without the `b` these rows were being "
    "cited as the binary. They are CO2 in 2.5 and 4 mol/kg NaCl and KCl at "
    "323.15/373.15/423.15 K and 2.6-18.2 MPa -- Tables 2 and 3 of the brine "
    "paper, the same tables whose gas-phase water content is already keyed "
    "HOU(2013b) in y_h2o.csv, and the transcription module that carries them "
    "says as much in its own docstring."
)

SOURCE_KEY_FIXES: dict[str, tuple[str, str]] = {
    "TAKENOUCHI": ("TAKENOUCHI(1964)",
                   "no year in the key. The 108 rows are y_H2O for CO2 + pure "
                   "water over 383-623 K and 100-1500 bar, which is the range "
                   "of Takenouchi & Kennedy's *binary* H2O-CO2 paper (110-350 "
                   "degC, to 1600 bar); the 1965 paper of the same authors is "
                   "NaCl brine, and no row here carries salt."),
    "TAKENOUSHI(1965)": ("TAKENOUCHI(1965)",
                         "surname misspelt. The 36 rows are CO2 in NaCl at 423 "
                         "K, 100-1200 bar, at total ion molalities 2.18 and "
                         "8.54 -- i.e. 1.09 and 4.27 mol/kg NaCl, exactly the "
                         "6 and 20 wt% solutions of Takenouchi & Kennedy "
                         "(1965)."),
    "TODHEIDE": ("TODHEIDE(1963)",
                 "no year in the key. The 103 rows are y_H2O for CO2 + pure "
                 "water to 3500 bar, which is the title range of Toedheide & "
                 "Franck (1963); it is the only Toedheide paper in the trove."),
    "HOU": ("HOU(2013)",
            "no year in the key, and two Hou 2013 papers are on record. The 32 "
            "rows are y_H2O for CO2 + *pure water* over 298-448 K, which is "
            "the title range of the binary CO2+H2O paper (Hou2013); the other "
            "(Hou2013b) is NaCl and KCl brine, already keyed separately in the "
            "same file as HOU(2013b)."),
    "Hou2013_JSCF78_T2": ("HOU(2013b)", _HOU_JSCF78),
    "Hou2013_JSCF78_T3": ("HOU(2013b)", _HOU_JSCF78),
    "BAMBERGE": ("BAMBERGER(2000)",
                 "surname truncated and no year. The 29 rows are y_H2O for CO2 "
                 "+ pure water over 323-353 K and 41-141 bar; Bamberger, "
                 "Sieder & Maurer (2000) report CO2 + water from 313 to 353 K "
                 "and 1 to 14 MPa."),
    "POULANI_2019": ("POULAIN(2019)",
                     "surname misspelt (Poulani for Poulain). The 96 rows are "
                     "CO2 in Na-Ca-K-Cl mixed brines, 323-423 K, to 199 bar, "
                     "which is Poulain et al. (2019) -- 48 new solubility "
                     "points in two synthetic Na-Ca-K-Cl brines to 20 MPa."),
    "KAMP(2007)": ("KAMPS(2007)",
                   "surname truncated (the author is Perez-Salado Kamps). The "
                   "26 rows are CO2 in KCl at 373 K and 6-90 bar, at 2 and 4 "
                   "mol/kg KCl, from the KCl series of Perez-Salado Kamps, "
                   "Meyer, Rumpf & Maurer (2007)."),
    "OSULLIVAN(1969)": ("OSULLIVAN(1970)",
                        "wrong year: these 32 CH4-in-NaCl rows and the 102 "
                        "rows already keyed OSULLIVAN(1970) are the *same* "
                        "paper. O'Sullivan & Smith (1970) measured nitrogen "
                        "AND methane in water and in aqueous NaCl from 50 to "
                        "125 degC and 100 to 600 atm; the rows under both keys "
                        "sit inside that single grid."),
    "PRAY(1957)": ("PRAY(1952)",
                   "wrong year. The 18 rows sit on the exact pressure grid of "
                   "Pray, Schweickert & Minnich (1952) Table II -- 100/200/300 "
                   "psi at 500 and 600 degF and 200/300/350 psi at 125 degF -- "
                   "and the transcribed mole fractions reproduce that table's "
                   "cm3(STP)/g values to three figures (0.39 cm3/g at 500 degF "
                   "and 100 psi -> x = 3.1e-4, transcribed 3.09e-4)."),
    "JUNG(1968)": ("JUNG(1971)",
                   "the published article is 1971. The 76 rows are H2 in pure "
                   "water over 373-573 K and 21-100 bar, which is exactly the "
                   "range of Jung, Knacke & Neuschuetz (1971) (to 300 degC and "
                   "100 atm); 1968 is the Aachen dissertation year, and no "
                   "1968 document exists in the trove."),
    "DOHRN": ("DOHRN(1993)",
              "no year in the key, and two Dohrn papers are on record. The "
              "curated transcription these 3 rows came from carries the header "
              "`#DOHRN (1993) -> Experimental measurements of phase equilibria "
              "for ternary and quaternary systems of glucose, water, CO2 and "
              "ethanol with a novel apparatus`, and the rows are y_H2O for CO2 "
              "+ water at 323 K; Dohrn1986 is a hydrogen/water/hydrocarbon "
              "paper and is keyed separately as DOHRN(1986) in solubility.csv."),
    "GUO(2015)": ("GUO(2016)",
                  "the key carries the ASAP year. Guo, Huang, Chen & Zhou's "
                  "Raman CO2-in-NaCl paper went online in December 2015 but "
                  "was assigned to J. Chem. Eng. Data 61(1), 466-474 (2016); "
                  "the 24 rows -- 373 K, 100-400 bar, 1/3/5 mol/kg NaCl -- are "
                  "on its 10/20/30/40 MPa grid."),
    "FROST(2013)": ("FROST(2014)",
                    "the key carries the ASAP year. Frost, Karakatsani, von "
                    "Solms, Richon & Kontogeorgis appeared online in December "
                    "2013 but was assigned to J. Chem. Eng. Data 59(4), "
                    "961-967 (2014); the 21 rows span 283-323 K and 47.8-194.9 "
                    "bar, inside that paper's 5-20 MPa methane + water set."),
    "BLANCO(1977)": ("BLANCO(1978)",
                     "wrong year. Blanco & Smith's high-pressure methane in "
                     "aqueous CaCl2 paper is J. Phys. Chem. 82(2), 186-191 "
                     "(1978); the 30 rows are CH4 in 1 mol/kg CaCl2 over "
                     "298-398 K and 101-608 bar, which is that paper's grid."),
    "TORIN(2022)": ("TORIN(2021)",
                    "wrong year. The paper -- Torin-Ollarves & Trusler, H2 in "
                    "NaCl brine, 323-423 K to 40 MPa at 2.5 mol/kg, matching "
                    "these 20 rows -- is Fluid Phase Equilibria 539 (2021) "
                    "113025; its own PDF metadata carries the 2021 volume."),
}


def apply_source_key_fix(raw: str) -> str:
    """Rewrite a demonstrably defective raw `source` value; else return it."""
    return SOURCE_KEY_FIXES.get(raw, (raw, ""))[0]


def _split_trailing_suffix(name: str) -> tuple[str, str]:
    """Split `ZHAOb` into ('ZHAO', 'b') but leave `Hou`, `Chabab`, `dosSantos` alone.

    A trailing lowercase letter is a disambiguating suffix only in the
    all-capitals spelling the transcriptions use (ZHAOb, RUMPFb, ZHAOc). In a
    mixed-case key the final lowercase letter is just part of the name, and
    stripping it produced nonsense like Ho2013u and Chaba2021b.
    """
    if len(name) >= 3 and name[-1].islower() and name[:-1].isupper():
        return name[:-1], name[-1]
    return name, ""


def parse_source_key(raw: str) -> tuple[str, str | None, str]:
    """Return (surname, year|None, suffix) for a raw `source` cell."""
    s = raw.split(" / ")[0].strip()          # drop "/ EXP_NaCl_T298K.txt"
    m = _YEAR_RE.match(s)
    if not m:
        name, suffix = _split_trailing_suffix(re.sub(r"[^A-Za-z]", "", s))
        return name.upper(), None, suffix.lower()
    name, pre = _split_trailing_suffix(re.sub(r"[^A-Za-z]", "", m.group("name")))
    suffix = pre + (m.group("post") or "")
    return name.upper(), m.group("year"), suffix.lower()


def canonical_id(surname: str, year: str | None, suffix: str) -> str:
    return f"{surname}{year or ''}{suffix.upper()}"


def display_key(surname: str, year: str | None, suffix: str) -> str:
    """A conventional citation key: Teymouri2017, Zhao2015b, Takenouchi."""
    name = surname.capitalize() if surname.isupper() else surname
    return f"{name}{year or ''}{suffix}"


# --------------------------------------------------------------------------
# bibtex
# --------------------------------------------------------------------------

# A bibtex key's trailing lowercase run is its disambiguating variant. It is
# not always a single letter -- `Mohammadi2004eth` distinguishes the ethane
# paper from `Mohammadi2004` -- and while this only allowed one letter, such
# keys fell out of the exact index entirely and had to be rescued by the
# looser (surname, year) lookup below, which cannot tell the two apart.
_BIB_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z'\-]*?)(\d{4})([a-z]{0,3})$")


def parse_bib(path: str) -> list[dict]:
    """Minimal brace-aware BibTeX reader. Returns dicts with key/type/fields/raw."""
    try:
        with open(path, "r", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []

    entries = []
    i = 0
    while True:
        at = text.find("@", i)
        if at < 0:
            break
        brace = text.find("{", at)
        if brace < 0:
            break
        etype = text[at + 1:brace].strip().lower()
        if etype in ("comment", "preamble", "string"):
            i = brace + 1
            continue
        depth, j = 0, brace
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = text[brace + 1:j]
        raw = text[at:j + 1]
        i = j + 1

        key, _, rest = body.partition(",")
        key = key.strip()
        if not key:
            continue
        fields = {}
        for name, value in _split_fields(rest):
            fields[name.lower()] = value
        entries.append({"key": key, "type": etype, "fields": fields,
                        "raw": raw, "origin": path})
    return entries


def _split_fields(rest: str):
    """Yield (name, value) from a bibtex entry body, respecting nesting."""
    depth = 0
    buf = []
    parts = []
    for ch in rest:
        if ch in "{(":
            depth += 1
        elif ch in "})":
            depth -= 1
        if ch == "," and depth <= 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    for p in parts:
        name, eq, value = p.partition("=")
        if not eq:
            continue
        value = value.strip()
        while value and value[0] in "{\"" and value[-1] in "}\"":
            value = value[1:-1].strip()
        yield name.strip(), " ".join(value.split())


def first_surname(author_field: str) -> str:
    """Best-effort first-author surname, uppercased and stripped to letters."""
    if not author_field:
        return ""
    first = re.split(r"\s+and\s+", author_field.strip(), maxsplit=1)[0]
    if "," in first:
        surname = first.split(",")[0]
    else:
        surname = first.split()[-1] if first.split() else ""
    return re.sub(r"[^A-Za-z]", "", surname).upper()


def dedupe_bib(entries: list[dict]) -> list[dict]:
    """Collapse the same citation key appearing in several .bib files.

    The paper repositories each carry their own refs.bib, so most entries show
    up two or three times. Left in, they made every year-less source key look
    'ambiguous' -- Meyer appeared to match both `Meyer2015` and `Meyer2015`.
    Where copies differ, a real record beats a placeholder one.
    """
    best: dict[str, dict] = {}
    for e in entries:
        prev = best.get(e["key"])
        if prev is None or (is_placeholder(prev) and not is_placeholder(e)):
            best[e["key"]] = e
    return list(best.values())


def _prefer(existing: dict | None, candidate: dict) -> dict:
    if existing is None:
        return candidate
    if is_placeholder(existing) and not is_placeholder(candidate):
        return candidate
    return existing


def index_bib(entries: list[dict]) -> dict:
    """Build lookup tables: exact key, (surname, year), and surname-only."""
    by_exact, by_name_year, by_name = {}, {}, defaultdict(list)
    for e in entries:
        m = _BIB_KEY_RE.match(e["key"])
        if m:
            name = m.group(1).upper()
            year = m.group(2)
            suffix = m.group(3).lower()
            cid = f"{name}{year}{suffix.upper()}"
            by_exact[cid] = _prefer(by_exact.get(cid), e)
            by_name_year[(name, year)] = _prefer(by_name_year.get((name, year)), e)
            by_name[name].append(e)
        # also index by the author field, which survives key-naming quirks
        aname = first_surname(e["fields"].get("author", ""))
        ayear = re.sub(r"[^0-9]", "", e["fields"].get("year", ""))[:4]
        if aname and len(ayear) == 4:
            key = (aname, ayear)
            by_name_year[key] = _prefer(by_name_year.get(key), e)
            if e not in by_name[aname]:
                by_name[aname].append(e)
    return {"exact": by_exact, "name_year": by_name_year, "name": by_name}


def _same_variant(entry: dict, cid: str, year: str, suffix: str) -> bool:
    """True if the bib record carries exactly the letter-variant the source does.

    The test has to run both ways. `bk.endswith(year)` alone said yes whenever
    the *record* had no variant, so source key MOHAMMADI(2004eth) happily
    claimed the plain `Mohammadi2004` record -- a different paper by the same
    authors in the same year. A variant on either side that the other lacks is
    a mismatch, and a mismatch is reported rather than asserted.
    """
    bk = re.sub(r"[^A-Za-z0-9]", "", entry["key"]).upper()
    if bk == cid:
        return True
    m = re.match(r"^([A-Z]+)(\d{4})([A-Z]*)$", bk)
    if not m:
        return False
    return m.group(2) == year and m.group(3) == suffix.upper()


def match_bib(surname, year, suffix, idx) -> tuple[dict | None, str, list[str]]:
    """Return (entry|None, how, candidates). Never guesses across ambiguity."""
    cid = canonical_id(surname, year, suffix)
    e = idx["exact"].get(cid)
    if e:
        return e, "key", []
    if year:
        e = idx["name_year"].get((surname, year))
        if e:
            if _same_variant(e, cid, year, suffix):
                return e, "key", []
            # The only record for this surname and year is a *variant* of it --
            # e.g. source MOHAMMADI(2004) against bib key Mohammadi2004eth.
            # Same author, same year, probably a different paper. Asserting it
            # would put a real DOI next to the wrong data, so don't.
            return None, "variant mismatch", [e["key"]]
        # multi-author run-together keys: CulbersonMcKetta1950 -> Culberson1950
        for cut in range(len(surname) - 2, 2, -1):
            e = idx["name_year"].get((surname[:cut], year))
            if e:
                if _same_variant(e, cid, year, suffix):
                    return e, "first author", []
                return None, "variant mismatch", [e["key"]]
    else:
        hits = idx["name"].get(surname, [])
        if len(hits) == 1:
            return hits[0], "surname (unique)", []
        if len(hits) > 1:
            return None, "ambiguous", sorted({h["key"] for h in hits})
    return None, "none", []


def is_placeholder(entry: dict) -> bool:
    blob = " ".join([entry["fields"].get("note", ""),
                     entry["fields"].get("title", ""),
                     entry["fields"].get("howpublished", "")])
    return bool(PLACEHOLDER_RE.search(blob))


def format_reference(entry: dict) -> str:
    f = entry["fields"]
    bits = []
    author = f.get("author", "")
    if author:
        names = re.split(r"\s+and\s+", _detex(author))
        shown = names[0] if "," in names[0] else " ".join(names[0].split()[-1:])
        if len(names) > 1:
            shown += " et al."
        bits.append(shown)
    if f.get("title"):
        bits.append(_detex(f["title"]))
    venue = f.get("journal") or f.get("booktitle") or f.get("institution") \
        or f.get("publisher") or f.get("school") or ""
    if venue:
        bits.append(_detex(venue))
    vol = f.get("volume", "")
    if vol:
        vol = f"**{vol}**"
        if f.get("number"):
            vol += f"({f['number']})"
        bits.append(vol)
    if f.get("pages"):
        bits.append(f["pages"].replace("--", "-"))
    if f.get("year"):
        bits.append(f["year"])
    return ", ".join(b for b in bits if b)


def _detex(s: str) -> str:
    # \ce{...} must go before the accent pass, which would otherwise read the
    # \c of \ce as a cedilla and leave a stray "e" glued to the formula --
    # that is where the manifest's old "eCO2" and "eSrCl2" came from.
    s = re.sub(r"\\ce\{([^{}]*)\}", r"\1", s)
    # accents: {\"o} -> o, \'{e} -> e, {\v s} -> s
    s = re.sub(r"\{?\\[`'\"^~=.vHruc]\s*\{?([A-Za-z])\}?\}?", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", s)
    s = s.replace("{", "").replace("}", "").replace("\\&", "&").replace("\\", "")
    s = s.replace("~", " ")
    return " ".join(s.split())


def doi_and_url(entry: dict) -> tuple[str, str]:
    f = entry["fields"]
    doi = f.get("doi", "").strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi).strip()
    if doi:
        return doi, f"https://doi.org/{doi}"
    url = f.get("url", "").strip()
    if url:
        return "", url
    return "", ""


# --------------------------------------------------------------------------
# data aggregation
# --------------------------------------------------------------------------

class SourceStats:
    def __init__(self, surname, year, suffix):
        self.surname, self.year, self.suffix = surname, year, suffix
        self.raw_keys = set()
        self.families = Counter()
        self.gases = set()
        self.quality = Counter()
        self.T = []
        self.P = []
        self.m = []
        self.salts = set()

    @property
    def cid(self):
        return canonical_id(self.surname, self.year, self.suffix)

    @property
    def rows(self):
        return sum(self.families.values())


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def collect(data_dir: str) -> tuple[dict, list[str], Counter]:
    stats: dict[str, SourceStats] = {}
    fixes_used: Counter = Counter()
    files = []
    for path in sorted(glob.glob(os.path.join(data_dir, "*.csv"))):
        if any(path.endswith(sfx) for sfx in SKIP_CSV_SUFFIXES):
            continue
        with open(path, newline="") as fh:
            reader = csv.DictReader(fh)
            if "source" not in (reader.fieldnames or []):
                continue
            files.append(os.path.basename(path))
            for row in reader:
                raw = (row.get("source") or "").strip()
                if not raw:
                    continue
                if raw in SOURCE_KEY_FIXES:
                    fixes_used[raw] += 1
                surname, year, suffix = parse_source_key(
                    apply_source_key_fix(raw))
                cid = canonical_id(surname, year, suffix)
                st = stats.get(cid)
                if st is None:
                    st = stats[cid] = SourceStats(surname, year, suffix)
                st.raw_keys.add(raw)
                st.families[(row.get("property") or "?").strip()] += 1
                gas = (row.get("gas") or "").strip()
                if gas:
                    st.gases.add(gas)
                q = (row.get("quality") or "").strip()
                if q:
                    st.quality[q] += 1
                for col, store in (("T_K", st.T), ("P_bar", st.P)):
                    v = _num(row.get(col))
                    if v is not None:
                        store.append(v)
                present, total = set(), 0.0
                for col in MOLALITY_COLS:
                    v = _num(row.get(col)) or 0.0
                    if v > 0:
                        present.add(col)
                        total += v
                st.m.append(total)
                st.salts.add(salt_label(present))
    return stats, files, fixes_used


def salt_label(present: set) -> str:
    if not present:
        return "pure water"
    key = frozenset(present)
    if key in SALT_BY_IONSET:
        return SALT_BY_IONSET[key]
    return "+".join(ION_LABEL[c] for c in MOLALITY_COLS if c in present)


def rng(vals, fmt="{:g}") -> str:
    vals = [v for v in vals if v is not None]
    if not vals:
        return "-"
    lo, hi = min(vals), max(vals)
    if lo == hi:
        return fmt.format(lo)
    return f"{fmt.format(lo)}-{fmt.format(hi)}"


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def _show(path: str) -> str:
    """Render a path relative to the repo, so no home directory leaks into the file."""
    try:
        rel = os.path.relpath(os.path.abspath(path), HERE)
    except ValueError:
        return path
    return rel if not rel.startswith(os.sep) else path


def render(stats, files, data_dir, bib_paths, missing_bibs, idx,
           fixes_used=None) -> tuple[str, list[dict]]:
    documented, no_doi, placeholder, needs = [], [], [], []
    matched_entries = []

    # One label per source, shared by both tables. A matched source is labelled
    # with the real bibtex key so the manifest and SOURCES.bib line up; an
    # unmatched one falls back to a key derived from the data.
    label: dict[str, str] = {}
    used: set[str] = set()

    ordered = sorted(stats.values(), key=lambda s: (-s.rows, s.cid))
    matches = {st.cid: match_bib(st.surname, st.year, st.suffix, idx)
               for st in ordered}

    # Unsuffixed source keys claim the plain label first, so MOHAMMADI(2004)
    # gets `Mohammadi2004` and MOHAMMADI(2004eth) becomes `Mohammadi2004 (eth)`
    # rather than the other way round.
    for st in sorted(ordered, key=lambda s: (bool(s.suffix), -s.rows, s.cid)):
        entry, _how, _c = matches[st.cid]
        base = entry["key"] if entry else display_key(st.surname, st.year, st.suffix)
        name = base
        if name in used:
            # two source keys resolving to one paper; keep them apart in the
            # tables without inventing a second citation for the same work
            name = f"{base} ({st.suffix})" if st.suffix else f"{base} (variant)"
            n = 2
            while name in used:
                name = f"{base} (variant {n})"
                n += 1
        used.add(name)
        label[st.cid] = name

    for st in ordered:
        entry, how, cands = matches[st.cid]
        if entry is None:
            needs.append((st, how, cands))
            continue
        if is_placeholder(entry):
            placeholder.append((st, entry, how))
            continue
        matched_entries.append(entry)
        doi, url = doi_and_url(entry)
        if doi:
            documented.append((st, entry, how, doi, url))
        else:
            no_doi.append((st, entry, how, doi, url))

    total_rows = sum(s.rows for s in stats.values())
    n = len(stats)
    out = []
    w = out.append

    w("# Sources")
    w("")
    w("**Every number in this benchmark was measured by someone else.** We hold")
    w("the primary papers locally in order to transcribe them; we do not and")
    w("cannot redistribute them. This manifest is how that circle is squared:")
    w("for each source it gives the full bibliographic reference, a DOI, a")
    w("resolvable URL, and exactly which rows of the benchmark came from it.")
    w("A reader can therefore obtain each paper through their own library and")
    w("reconstruct the entire database from primary sources -- without us")
    w("redistributing a single copyrighted page.")
    w("")
    w("> Generated by `tools/make_sources.py`. Do not edit by hand: re-run the")
    w("> script and commit the diff. It is generated precisely so that the")
    w("> coverage figures below cannot drift away from what the CSVs say.")
    w("")
    w(f"Generated {date.today().isoformat()} from `{_show(data_dir)}`")
    w("")
    w(f"- data files read: {len(files)} (`" + "`, `".join(files) + "`)")
    w(f"- rows: {total_rows:,}")
    w(f"- distinct sources: {n}")
    w(f"- fully documented (reference + DOI): **{len(documented)}**")
    w(f"- reference known, DOI missing: **{len(no_doi)}**")
    w(f"- placeholder citation, needs replacing: **{len(placeholder)}**")
    w(f"- no bibliographic record at all: **{len(needs)}**")
    w("")
    rows_ok = sum(s.rows for s, *_ in documented)
    rows_nodoi = sum(s.rows for s, *_ in no_doi)
    rows_ph = sum(s.rows for s, *_ in placeholder)
    rows_need = sum(s.rows for s, *_ in needs)
    w(f"By row count: {rows_ok:,} fully documented, {rows_nodoi:,} reference-only, "
      f"{rows_ph:,} placeholder, {rows_need:,} undocumented "
      f"({100.0 * (rows_ok + rows_nodoi) / total_rows:.1f} % of rows carry a real reference).")
    w("")
    if no_doi:
        w("The reference-only entries are shown below with *none on record* in")
        w("the DOI column. That is not a lookup we skipped: each was searched")
        w("for and no DOI exists. They are doctoral theses, association and")
        w("agency research reports, and papers in journals that were never")
        w("retrospectively registered. Where a stable locator exists instead --")
        w("a repository handle, a report archive -- it is given in the URL")
        w("column.")
        w("")
    w("Bibliographic records were read from:")
    for p in bib_paths:
        w(f"- `{_show(p)}`")
    for p in missing_bibs:
        w(f"- `{_show(p)}` *(not present on this machine -- skipped)*")
    w("")
    w("The manifest is split into two tables keyed on the same citation key:")
    w("a bibliography, and a coverage table. Eleven columns in one table is not")
    w("readable; two joined on the key is.")
    w("")

    # ---- bibliography -----------------------------------------------------
    w("## Bibliography")
    w("")
    w("| Citation key | Reference | DOI | URL |")
    w("|---|---|---|---|")
    for st, entry, how, doi, url in documented + no_doi:
        key = label[st.cid]
        ref = format_reference(entry)
        note = "" if how == "key" else f" <sup>({how})</sup>"
        doi_cell = f"`{doi}`" if doi else "*none on record*"
        url_cell = f"[link]({url})" if url else "-"
        w(f"| `{key}` | {ref}{note} | {doi_cell} | {url_cell} |")
    w("")

    # ---- coverage ---------------------------------------------------------
    w("## Coverage")
    w("")
    w("`m` is total ion molality (sum over Na+, K+, Ca2+, Mg2+, Cl-, SO4 2-),")
    w("in mol per kg of water. Quality codes are R (recommended), T (tentative),")
    w("U (uncertain).")
    w("")
    w("| Citation key | Property families (rows) | Gas | Salt system | T [K] | P [bar] | m [mol/kg] | R/T/U |")
    w("|---|---|---|---|---|---|---|---|")
    for st in ordered:
        key = label[st.cid]
        fams = ", ".join(f"{f} ({c})" for f, c in st.families.most_common())
        gases = ", ".join(sorted(st.gases)) or "-"
        salts = ", ".join(sorted(st.salts))
        q = "/".join(str(st.quality.get(c, 0)) for c in "RTU")
        w(f"| `{key}` | {fams} | {gases} | {salts} | {rng(st.T)} | "
          f"{rng(st.P)} | {rng(st.m)} | {q} |")
    w("")

    # ---- source-key corrections -------------------------------------------
    if fixes_used:
        w("## Source-key corrections")
        w("")
        w("The `source` cell of these rows does not name the paper they were")
        w("transcribed from: a surname is misspelt or truncated, a year is")
        w("missing, or the year belongs to a thesis rather than to the")
        w("published article the numbers were read out of. The generator")
        w("rewrites them to the identity given below before matching against")
        w("the bibliography. Nothing here was inferred from the name alone --")
        w("each was settled by reading the primary paper held locally and")
        w("checking it against the rows' own T, P, salt and composition grid,")
        w("and the reasoning is given in full so it can be audited. The raw")
        w("cell is left untouched in the CSVs and is still what you would grep")
        w("for; it is reproduced verbatim in the first column.")
        w("")
        w("| Raw `source` in the data | Rows | Read as | Why |")
        w("|---|---:|---|---|")
        for raw, n in sorted(fixes_used.items(), key=lambda t: (-t[1], t[0])):
            fixed, why = SOURCE_KEY_FIXES[raw]
            w(f"| `{raw}` | {n} | `{fixed}` | {why} |")
        w("")

    # ---- placeholders -----------------------------------------------------
    if placeholder:
        w("## Placeholder citations -- must be replaced before release")
        w("")
        w("A bibliographic record exists but is explicitly marked as provisional.")
        w("It is reproduced here rather than being presented as a real citation.")
        w("")
        w("| Citation key | Rows | Record found | What it says |")
        w("|---|---:|---|---|")
        for st, entry, how in placeholder:
            key = label[st.cid]
            note = _detex(entry["fields"].get("note", "")
                          or entry["fields"].get("title", ""))[:220]
            w(f"| `{key}` | {st.rows} | `{entry['key']}` in "
              f"`{os.path.basename(entry['origin'])}` | {note} |")
        w("")

    # ---- needs citation ---------------------------------------------------
    w("## Needs citation")
    w("")
    if not needs:
        w("None. Every source key resolves to a bibliographic record.")
    else:
        w("These source keys carry data but have **no bibliographic record** in")
        w("any .bib file the generator was given. Nothing has been invented for")
        w("them: no reference, no DOI, no URL. Each needs a real citation found")
        w("and added to a .bib file, after which this table shrinks on its own.")
        w("")
        w("| Source key | Rows | Property families | Gas | Raw `source` values in the data | Note |")
        w("|---|---:|---|---|---|---|")
        for st, how, cands in sorted(needs, key=lambda t: -t[0].rows):
            key = label[st.cid]
            fams = ", ".join(sorted(st.families))
            gases = ", ".join(sorted(st.gases)) or "-"
            raws = ", ".join(f"`{r}`" for r in sorted(st.raw_keys)[:3])
            if len(st.raw_keys) > 3:
                raws += f" *(+{len(st.raw_keys) - 3} more)*"
            if how == "ambiguous":
                note = ("no year in the key; matches several records: "
                        + ", ".join(f"`{c}`" for c in cands))
            elif how == "variant mismatch":
                note = ("same author and year as "
                        + ", ".join(f"`{c}`" for c in cands)
                        + ", but that is a lettered variant -- likely a different "
                          "paper, so it has not been asserted here")
            elif st.year is None:
                note = "no year in the source key"
            else:
                note = "not found in any .bib"
            w(f"| `{key}` | {st.rows} | {fams} | {gases} | {raws} | {note} |")
    w("")
    return "\n".join(out) + "\n", matched_entries


def _undated(text: str) -> str:
    """Drop the generation-date line so --check does not fail on the calendar."""
    return "\n".join(ln for ln in text.splitlines()
                     if not ln.startswith("Generated "))


def render_bib(entries: list[dict]) -> str:
    seen, out = set(), []
    out.append("% Generated by tools/make_sources.py -- do not edit by hand.")
    out.append("% Contains only records harvested verbatim from existing .bib files")
    out.append("% for sources that actually appear in the benchmark data. Sources")
    out.append("% without a record are listed in SOURCES.md under 'Needs citation'")
    out.append("% and are deliberately absent here rather than invented.")
    out.append("")
    for e in sorted(entries, key=lambda x: x["key"].lower()):
        if e["key"] in seen:
            continue
        seen.add(e["key"])
        out.append(e["raw"].strip())
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--bib", action="append", default=None,
                    help="bibtex file to harvest (repeatable)")
    ap.add_argument("--out", default=os.path.join(HERE, "SOURCES.md"))
    ap.add_argument("--bib-out", default=os.path.join(HERE, "SOURCES.bib"))
    ap.add_argument("--stdout", action="store_true", help="print instead of writing")
    ap.add_argument("--check", action="store_true",
                    help="verify the committed SOURCES.* are what this script "
                         "would write; change nothing. Exit 1 if they drift. "
                         "The generation-date line is ignored, so re-running "
                         "on a later day is not a difference.")
    args = ap.parse_args()

    if not os.path.isdir(args.data_dir):
        print(f"error: data dir not found: {args.data_dir}", file=sys.stderr)
        return 2

    # Never read back the file we are about to write: a stale harvested copy
    # would otherwise outrank a corrected record upstream.
    candidates = [p for p in (args.bib or DEFAULT_BIBS)
                  if os.path.abspath(p) != os.path.abspath(args.bib_out)]
    found = [p for p in candidates if os.path.isfile(p)]
    missing = [p for p in candidates if not os.path.isfile(p)]

    entries = []
    for p in found:
        entries.extend(parse_bib(p))
    entries = dedupe_bib(entries)
    idx = index_bib(entries)

    stats, files, fixes_used = collect(args.data_dir)
    if not stats:
        print(f"error: no source-bearing CSVs in {args.data_dir}", file=sys.stderr)
        return 2

    md, matched = render(stats, files, args.data_dir, found, missing, idx,
                         fixes_used)

    if args.stdout:
        sys.stdout.write(md)
        return 0

    if args.check:
        drift = []
        for path, fresh in ((args.out, md), (args.bib_out, render_bib(matched))):
            if not os.path.isfile(path):
                drift.append(f"{_show(path)} is missing")
                continue
            with open(path) as fh:
                committed = fh.read()
            if _undated(committed) != _undated(fresh):
                drift.append(f"{_show(path)} differs from what this script "
                             "would write now")
        if drift:
            print("make_sources --check FAILED:")
            for d in drift:
                print(" -", d)
            print("Re-run `python3 tools/make_sources.py` and commit the diff.")
            return 1
        print(f"make_sources --check: SOURCES.md and SOURCES.bib are current "
              f"({len(stats)} sources over "
              f"{sum(s.rows for s in stats.values()):,} rows)")
        return 0

    with open(args.out, "w") as fh:
        fh.write(md)
    with open(args.bib_out, "w") as fh:
        fh.write(render_bib(matched))

    print(f"{len(stats)} sources over {sum(s.rows for s in stats.values()):,} rows "
          f"from {len(files)} csv files")
    print(f"  {len(matched)} bibliographic records written to {args.bib_out}")
    print(f"  manifest written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
