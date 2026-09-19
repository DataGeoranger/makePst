"""The version in pyproject.toml, the package's fallback and the manifest agree."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import makepst  # noqa: E402


def test_versions_agree():
    with open(os.path.join(ROOT, 'pyproject.toml')) as f:
        declared = re.search(r'^version\s*=\s*"([^"]+)"', f.read(), re.M).group(1)
    with open(os.path.join(ROOT, 'makepst', '__init__.py')) as f:
        fallback = re.search(r"__version__\s*=\s*'([^']+)'", f.read()).group(1)
    assert fallback == declared, 'update the fallback in makepst/__init__.py'
    assert makepst.__version__ == declared
