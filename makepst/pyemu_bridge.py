"""Hand a Pst to pyEMU and back.

pyEMU (https://github.com/pypest/pyemu) is the toolkit for everything makepst leaves alone:
linear and ensemble uncertainty analysis, Jacobian handling, geostatistics, PstFrom. The
bridge goes through a temporary control file in each direction, so it depends only on the
file format both sides speak, not on pyEMU's internal table layout.
"""
import os
import tempfile

from .reader import read_pst
from .writer import write_pst


def _pyemu():
    try:
        import pyemu
    except ImportError as e:
        raise ImportError('pyemu is not installed; pip install pyemu') from e
    return pyemu


def to_pyemu(pst):
    """A pyemu.Pst with the same content as `pst` (control values, tables, ++ options)."""
    pyemu = _pyemu()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'makepst.pst')
        write_pst(pst, path, dump_tpl=False, version=1)
        return pyemu.Pst(path)


def from_pyemu(ppst):
    """A makepst Pst from a pyemu.Pst (written to a temporary control file and read back)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'pyemu.pst')
        ppst.write(path)
        pst = read_pst(path)
    pst.version = 1
    return pst
