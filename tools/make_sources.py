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

WHAT IT WILL NOT DO
-------------------
It never invents a reference. A source key with no bibliographic record in any
of the .bib files it was given is reported, by name, in a "needs citation"
section. A record that is itself marked as a placeholder is reported in a
"placeholder citation" section. Neither is quietly filled in.

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
_SIB = os.path.normpath(os.path.join(HERE, ".."))

DEFAULT_DATA_DIR = os.path.join(_SIB, "EoS_Benchmark", "code", "bench", "data")

# Bibliographic records are harvested from wherever they already exist. Missing
# files are skipped with a note rather than being an error, so the script still
# runs on a machine that only has this repository.
DEFAULT_BIBS = [
    os.path.join(HERE, "SOURCES.bib"),
    os.path.join(_SIB, "EoS_Benchmark", "paper", "references.bib"),
    os.path.join(_SIB, "Multi_Salt", "papers", "multisalt", "refs.bib"),
    os.path.join(_SIB, "Multi_Salt", "papers", "multisalt", "paper_IV", "refs.bib"),
    os.path.join(_SIB, "Multi_Salt", "papers", "multisalt", "two_papers",
                 "part_II_threephase", "refs.bib"),
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

_BIB_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z'\-]*?)(\d{4})([a-z]?)$")


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


def _same_variant(entry: dict, cid: str, year: str) -> bool:
    """True if the bib key carries no letter-variant the source key lacks."""
    bk = re.sub(r"[^A-Za-z0-9]", "", entry["key"]).upper()
    return bk == cid or bk.endswith(year)


def match_bib(surname, year, suffix, idx) -> tuple[dict | None, str, list[str]]:
    """Return (entry|None, how, candidates). Never guesses across ambiguity."""
    cid = canonical_id(surname, year, suffix)
    e = idx["exact"].get(cid)
    if e:
        return e, "key", []
    if year:
        e = idx["name_year"].get((surname, year))
        if e:
            if _same_variant(e, cid, year):
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
                if _same_variant(e, cid, year):
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
    # accents first: {\"o} -> o, \'{e} -> e, {\v s} -> s
    s = re.sub(r"\{?\\[`'\"^~=.vHruc]\s*\{?([A-Za-z])\}?\}?", r"\1", s)
    s = re.sub(r"\\ce\{([^}]*)\}", r"\1", s)
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


def collect(data_dir: str) -> tuple[dict, list[str]]:
    stats: dict[str, SourceStats] = {}
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
                surname, year, suffix = parse_source_key(raw)
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
    return stats, files


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


def render(stats, files, data_dir, bib_paths, missing_bibs, idx) -> tuple[str, list[dict]]:
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

    stats, files = collect(args.data_dir)
    if not stats:
        print(f"error: no source-bearing CSVs in {args.data_dir}", file=sys.stderr)
        return 2

    md, matched = render(stats, files, args.data_dir, found, missing, idx)

    if args.stdout:
        sys.stdout.write(md)
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
