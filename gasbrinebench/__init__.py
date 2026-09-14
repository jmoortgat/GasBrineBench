"""GasBrineBench: read, filter and export the benchmark dataset.

A thin, honest reader for the CSVs in ``data/``. It adds no numbers to the
database: everything it returns is either a row as transcribed, or a quantity
derived from such rows by an identity documented in ``SCHEMA.md``.

Five-minute tour
----------------
>>> import gasbrinebench as gbb
>>> gbb.__version__
'0.9.0-pre'

Load everything. The 144 ``lle-regime`` rows -- propane points whose heavy
phase is a liquid, so they are mutual solubilities and not gas solubilities --
are excluded by default; pass ``exclude_tags=None`` for the raw 5,846:

>>> df = gbb.load()
>>> len(df)
5702

Filter on any axis, in one call or several:

>>> co2 = gbb.load('solubility', gas='co2', property='solubility_molality')
>>> len(co2)
937
>>> hot_brine = gbb.select(co2, T=(373, 425), ionic_strength=(2, None))
>>> len(hot_brine)
385

Derived composition quantities:

>>> float(gbb.ionic_strength(co2).max())
18.0
>>> gbb.salt_system_kind(co2).value_counts().to_dict()
{'single-salt': 615, 'mixed-salt': 322}

Both mole-fraction siblings of a solubility, joined onto one row:

>>> p = gbb.solubility_pairs(co2)
>>> list(p.columns[-4:])
['solubility_molality', 'xc_saltfree', 'xc_saltfree_derived', 'xc_saltinclusive']

What a selection contains:

>>> gbb.inventory(df, by='gas').loc['h2', 'rows']
437

Export. CSV always works; Parquet and HDF5 raise
:class:`~gasbrinebench.export.MissingDependencyError` naming the one package
to install, rather than a traceback from inside pandas:

>>> import os, tempfile
>>> _ = gbb.write(co2, os.path.join(tempfile.mkdtemp(), 'co2.csv'))
>>> _ = gbb.write(co2, 'co2.parquet')                       # doctest: +SKIP

See also
--------
gasbrinebench.interop
    Why no PHREEQC or Geochemist's Workbench exporter is shipped, and the
    column mapping to write your own.
"""

from ._version import __version__
from . import derived, export, filters, interop, loader, pairs, summary, vocab
from .derived import (
    charge_imbalance,
    ionic_strength,
    ions_present,
    molality_from_xc_saltfree,
    salt_system,
    salt_system_kind,
    total_molality,
    with_derived,
    xc_saltfree_from_molality,
    xc_saltinclusive_from_molality,
)
from .export import (
    MissingDependencyError,
    to_pandas,
    write,
    write_csv,
    write_hdf5,
    write_parquet,
)
from .filters import select
from .interop import phreeqc_column_map
from .loader import available_families, data_dir, load, load_family
from .pairs import solubility_pairs
from .summary import coverage, inventory, sources
from .vocab import (
    COLUMNS,
    FAMILIES,
    GASES,
    IONS,
    ION_CHARGE,
    PROPERTIES,
    QUALITY_CODES,
    TAGS,
    UNITS,
)

__all__ = [
    "__version__",
    # loading
    "load",
    "load_family",
    "available_families",
    "data_dir",
    # filtering
    "select",
    # derived
    "ionic_strength",
    "total_molality",
    "charge_imbalance",
    "salt_system",
    "salt_system_kind",
    "ions_present",
    "with_derived",
    "xc_saltfree_from_molality",
    "xc_saltinclusive_from_molality",
    "molality_from_xc_saltfree",
    "solubility_pairs",
    # inventory
    "inventory",
    "coverage",
    "sources",
    # export
    "write",
    "write_csv",
    "write_parquet",
    "write_hdf5",
    "to_pandas",
    "MissingDependencyError",
    # interop
    "phreeqc_column_map",
    # vocabulary
    "COLUMNS",
    "FAMILIES",
    "GASES",
    "IONS",
    "ION_CHARGE",
    "PROPERTIES",
    "QUALITY_CODES",
    "TAGS",
    "UNITS",
    # submodules
    "derived",
    "export",
    "filters",
    "interop",
    "loader",
    "pairs",
    "summary",
    "vocab",
]
