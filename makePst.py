"""Compatibility entry point: same command line as the old single-file makePst.py.

    python makePst.py out.pst regul --set_ctl_xls book.xlsm,CONTROL --add_par_xls book.xlsm,PAR ...
    python makePst.py dump  run.pst run.xlsx
    python makePst.py update book.xlsm --par run.par

The makepst/ package must sit next to this file.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from makepst.cli import main  # noqa: E402

if __name__ == '__main__':
    main()
