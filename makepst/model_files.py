"""Model input files from templates, observation values from instruction files: what PEST's
TEMPCHEK and INSCHEK do, in Python.

The number writer follows PEST's WRTSIG: a value is written into its parameter space with as
much precision as the space allows, in fixed or exponential notation, with the decimal point
kept unless the model was declared to read without one (DPOINT nopoint), and the same word in
every space a parameter occupies, sized for the narrowest.
"""
import math
import re

import pandas as pd


class FieldError(ValueError):
    """A number that cannot be written into its parameter space."""


# ---------------------------------------------------------------------- numbers
def write_number(value, width, precis='single', dpoint='point'):
    """A number written into `width` characters with the most precision that fits.

    Fixed or exponential notation, whichever carries more of the value (the shorter on a tie,
    then fixed); the exponent form may carry more than one digit before the point when that
    shortens the exponent (123.4568E9). The decimal point is always present unless `dpoint` is
    'nopoint', when it is dropped where that gains a digit (12345E-3, 123). Single precision
    uses at most 15 characters and, like PEST, 8 significant digits once the space allows the
    E13.7 form; double 23 and 16. FieldError when the space is too narrow or the exponent is
    beyond the precision's range (PEST's messages).
    """
    value = float(value)
    single = str(precis).lower() != 'double'
    nopoint = str(dpoint).lower() == 'nopoint'
    lw = min(15 if single else 23, int(width))
    cap = lw if lw < (13 if single else 22) else (8 if single else 16)     # significant digits
    if value != 0.0:
        jexp = int(math.floor(math.log10(abs(value))))
        if abs(jexp) > (38 if single else 275):
            raise FieldError(f'number too large or small for {"single" if single else "double"} precision protocol')
    else:
        jexp = 0
    best = None
    for kind, s in _candidates(value, jexp, lw, cap, nopoint):
        if len(s) > lw:
            continue
        got = float(s)
        if value != 0.0 and got == 0.0:                     # not a single significant digit
            continue
        key = (abs(got - value), len(s), kind)
        if best is None or key < best[0]:
            best = (key, s)
    if best is None:
        raise FieldError('field width too small to represent number')
    return best[1]


def _candidates(value, jexp, lw, cap, nopoint):
    """(kind, text) in order of growing length: fixed with 0.. decimals, then exponential."""
    for d in range(0, max(0, cap - 1 - jexp) + 1):
        s = f'{value:.{d}f}' + ('.' if d == 0 else '')
        if d and len(s) > lw and (s.startswith('0.') or s.startswith('-0.')):
            s = s.replace('0.', '.', 1)                     # Fortran drops the optional zero
        if nopoint and d == 0:
            yield 1, s[:-1]
        yield 0, s
        if len(s) > lw:
            break
    for p in range(1, cap + 1):                             # p significant digits
        m, e = f'{value:.{p - 1}e}'.split('e')
        sign, digits, e = ('-' if m.startswith('-') else ''), m.lstrip('-').replace('.', ''), int(e)
        shortest = None
        for k in range(p):                                  # k + 1 digits before the point
            s = f'{sign}{digits[:k + 1]}.{digits[k + 1:]}E{e - k}'
            yield 2, s
            shortest = s if shortest is None or len(s) < len(shortest) else shortest
        if nopoint:
            bare = f'{sign}{digits}E{e - p + 1}'
            yield 3, bare
            shortest = bare if len(bare) < len(shortest) else shortest
        if len(shortest) > lw:
            break


# ---------------------------------------------------------------------- templates
def parse_template(path):
    """(delimiter, body lines, spaces): spaces[i] lists (start, end, name) for body line i."""
    with open(path, errors='replace') as f:
        head = f.readline().split()
        lines = f.read().splitlines()
    if len(head) != 2 or head[0].lower() not in ('ptf', 'jtf'):
        raise ValueError(f'first line must be "ptf <delimiter>", got {" ".join(head)!r}')
    d = head[1]
    pat = re.compile(re.escape(d) + '(.*?)' + re.escape(d))
    spaces = [[(m.start(), m.end(), m.group(1).strip().lower()) for m in pat.finditer(ln)] for ln in lines]
    return d, lines, spaces


def fill_template(path, values, precis='single', dpoint='point', report_missing=True):
    """Model input text from a template and parameter values {name: value} (scale and offset applied).

    Returns (text, problems): the file's text (None when there are problems) and TEMPCHEK's
    messages, one per parameter, for names missing from `values` and for values that cannot be
    written into their space. Each parameter gets one word, sized for its narrowest space and
    right-justified in every space, as PEST writes it.
    """
    _, lines, spaces = parse_template(path)
    width = {}
    for row in spaces:
        for s, e, name in row:
            width[name] = min(width.get(name, e - s), e - s)
    problems, word = [], {}
    for name, w in width.items():
        if name not in values:
            if report_missing:
                problems.append(f'parameter "{name}" cited in the template has no value')
            continue
        try:
            word[name] = write_number(values[name], w, precis, dpoint)
        except FieldError as e:
            problems.append(f'parameter "{name}" ({float(values[name]):g} in {w} characters): {e}')
    if problems or len(word) < len(width):
        return None, problems
    out = []
    for ln, row in zip(lines, spaces):
        for s, e, name in reversed(row):
            ln = ln[:s] + word[name].rjust(e - s) + ln[e:]
        out.append(ln)
    return '\n'.join(out) + '\n', []


def fit_problems(path, values, precis='single', dpoint='point'):
    """Only the values that cannot be written into their space (names absent from `values` are ignored)."""
    return fill_template(path, values, precis, dpoint, report_missing=False)[1]


def write_model_input(tpl_path, values, out_path, precis='single', dpoint='point'):
    """Write the model input file `tpl_path` describes; returns fill_template's problems (file written only if none)."""
    text, problems = fill_template(tpl_path, values, precis, dpoint)
    if not problems:
        with open(out_path, 'w') as f:
            f.write(text)
    return problems


def scaled_values(par):
    """{name: PARVAL1 * SCALE + OFFSET} from a parameter table (SCALE / OFFSET default to 1 / 0).

    `par` is Pst.par (PARNME column) or read_par's frame (PARNME index).
    """
    names = par['PARNME'] if 'PARNME' in par else par.index
    val = pd.to_numeric(par['PARVAL1'], errors='coerce')
    scale = pd.to_numeric(par['SCALE'], errors='coerce').fillna(1.0) if 'SCALE' in par else 1.0
    offset = pd.to_numeric(par['OFFSET'], errors='coerce').fillna(0.0) if 'OFFSET' in par else 0.0
    out = val * scale + offset
    return {str(n).strip().lower(): float(v) for n, v in zip(names, out) if pd.notna(v)}


def par_header(parfile):
    """(precis, dpoint) from the first line of a .par file; ('single', 'point') for anything else."""
    try:
        with open(parfile, errors='replace') as f:
            head = f.readline().split()
    except OSError:
        return 'single', 'point'
    if len(head) >= 2 and head[0].lower() in ('single', 'double') and head[1].lower() in ('point', 'nopoint'):
        return head[0].lower(), head[1].lower()
    return 'single', 'point'


# ---------------------------------------------------------------------- observations
def write_obf(path, values):
    """INSCHEK's observation value file: one 'name  value' line per observation read."""
    with open(path, 'w') as f:
        for name, v in values.items():
            f.write(f' {name:<20}  {v:.15G}\n')


def read_obf(path):
    """{name: value} from an observation value file (INSCHEK's .obf)."""
    df = pd.read_csv(path, sep=r'\s+', header=None, names=['OBSNME', 'value'])
    return {str(n).lower(): float(v) for n, v in zip(df['OBSNME'], df['value'])}
