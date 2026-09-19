"""Provenance manifest: which inputs, which command, which version produced an output.

Written as a sidecar `<output>.manifest.json` next to the file a command produces, so a
control file or an updated workbook can be traced back to the exact workbook (by hash),
sheets, result files and command line that made it.
"""
import datetime as _dt
import getpass
import hashlib
import json
import os
import platform
import sys


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(chunk), b''):
            h.update(block)
    return h.hexdigest()


def _file_record(path):
    st = os.stat(path)
    return {
        'path': os.path.abspath(path),
        'sha256': sha256(path),
        'size': st.st_size,
        'modified': _dt.datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec='seconds'),
    }


class Manifest:
    def __init__(self, command, argv=None):
        from . import __version__
        import pandas
        self.data = {
            'makepst': __version__,
            'command': command,
            'argv': list(sys.argv[1:] if argv is None else argv),
            'created': _dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'user': _safe(getpass.getuser),
            'host': platform.node(),
            'cwd': os.getcwd(),
            'python': platform.python_version(),
            'pandas': pandas.__version__,
            'platform': platform.platform(),
            'sources': [],
            'output': None,
        }
        self._by_path = {}

    def add_source(self, path, sheet=None, role=None):
        """Record an input file; the same file read several times gets one entry with all its sheets."""
        key = os.path.abspath(path)
        rec = self._by_path.get(key)
        if rec is None:
            rec = _file_record(path)
            if role:
                rec['role'] = role
            self._by_path[key] = rec
            self.data['sources'].append(rec)
        if sheet and sheet not in rec.setdefault('sheets', []):
            rec['sheets'].append(sheet)
        if role and 'role' not in rec:
            rec['role'] = role
        return rec

    def set_output(self, path, **extra):
        self.data['output'] = dict(_file_record(path), **extra)

    def add(self, **fields):
        self.data.update(fields)

    def write(self, path=None):
        """Write next to the output as <output>.manifest.json (or to `path`); returns the path."""
        if path is None:
            path = self.data['output']['path'] + '.manifest.json'
        with open(path, 'w') as f:
            json.dump(self.data, f, indent=2)
        return path


def _safe(fn):
    try:
        return fn()
    except Exception:            # no login name in some CI containers
        return None
