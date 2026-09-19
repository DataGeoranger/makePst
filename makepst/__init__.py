"""Build, read and round-trip PEST control files from spreadsheet tables."""
__version__ = '0.1.0'

from .excel import load_table, to_workbook, update_workbook
from .provenance import Manifest
from .pst import Pst, read_ensemble, read_obs_ensemble, read_par, read_res
from .reader import from_text, read_pst
from .writer import to_text, write_pst


def to_pyemu(pst):
    from .pyemu_bridge import to_pyemu as _to
    return _to(pst)


def from_pyemu(ppst):
    from .pyemu_bridge import from_pyemu as _from
    return _from(ppst)

__all__ = ['Pst', 'read_pst', 'from_text', 'write_pst', 'to_text',
           'load_table', 'to_workbook', 'update_workbook', 'read_par', 'read_res', 'read_ensemble', 'read_obs_ensemble', 'Manifest', '__version__', 'to_pyemu', 'from_pyemu']
