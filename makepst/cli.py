"""Command line: build (Excel/CSV -> pst), dump (pst -> Excel), update (values -> existing workbook),
parrep (.par values -> pst), init (starter workbook), validate (pestchek-style checks), diff (compare two)."""
import argparse
import os
import shlex
import sys

from . import __version__
from .excel import expand_spec, load_table, to_workbook, update_workbook
from .provenance import Manifest
from .pst import Pst, read_par
from .reader import read_pst
from .writer import write_pst

TABLES = ('pargp', 'par', 'tied', 'prior', 'obs', 'obsgp', 'io', 'pp', 'comment')
WORKBOOK_EXT = ('.xlsx', '.xlsm', '.xls')


def _spec_parts(spec):
    """'book.xlsx,SHEET' -> (book.xlsx, SHEET); 'file.csv' -> (file.csv, None)."""
    if ',' in spec:
        path, sheet = spec.rsplit(',', 1)
        return path, sheet
    return spec, None


def _build_parser(p):
    p.add_argument('pstfile', help='control file to write, or a workbook whose BUILD sheet holds the command')
    p.add_argument('mode', nargs='?', default=None,
                   help='estimation | regularisation | prediction | pareto (default: CONTROL sheet, else estimation)')
    p.add_argument('--set_ctl_xls', metavar='BOOK,SHEET', help='CONTROL sheet: NAME / VALUE columns')
    p.add_argument('--set_ctl_csv', metavar='CSV')
    for t in TABLES:
        p.add_argument(f'--add_{t}_xls', action='append', default=[], metavar='BOOK,SHEET',
                       help='sheet name may be a glob, e.g. book.xlsm,PAR_*' if t == 'par' else argparse.SUPPRESS)
        p.add_argument(f'--add_{t}_csv', action='append', default=[], metavar='CSV')
    p.add_argument('--add_comment', action='append', default=[], metavar='TEXT')
    p.add_argument('--fill_parval', metavar='FILE',
                   help='take PARVAL1 from a PEST .par file or a PESTPP-IES case.N.par.csv')
    p.add_argument('--real', metavar='NAME', help='realization for --fill_parval from an ensemble (default base)')
    p.add_argument('--ss', action='store_true', help='steady state: drop ss*/sy* parameters and groups')
    p.add_argument('--no_dump_tpl', action='store_true', help="don't write dump.tpl next to the pst")
    p.add_argument('--no_manifest', action='store_true', help="don't write <pst>.manifest.json")
    p.add_argument('--out', metavar='PST', help='with a workbook: where to write (default: the name in the BUILD sheet)')
    fmt_ = p.add_mutually_exclusive_group()
    fmt_.add_argument('--v2', action='store_true', help='write a PEST++ version-2 file (external csv tables beside it)')
    fmt_.add_argument('--v1', action='store_true', help='write the classic format (default for tables)')


def build_pst(args, manifest=None):
    """The Pst described by parsed `build` arguments (nothing written)."""
    def table(spec, role):
        if manifest is not None:
            path, sheet = _spec_parts(spec)
            manifest.add_source(path, sheet, role)
        return load_table(spec)

    control = None
    if args.set_ctl_xls:
        control = table(args.set_ctl_xls, 'control')
    elif args.set_ctl_csv:
        control = table(args.set_ctl_csv, 'control')

    pst = Pst(ss=args.ss)
    if control is not None:
        pst.set_control(control)
    if args.mode:
        pst.pestmode = Pst(args.mode).pestmode
    print(f'Building a {pst.pestmode} control file...')

    for c in args.add_comment:
        pst.add_comment(comment=c)
    for t in TABLES:
        for pattern in getattr(args, f'add_{t}_xls') + getattr(args, f'add_{t}_csv'):
            for spec in expand_spec(pattern):            # book,PAR_* -> every matching sheet
                print(f'Adding {t:8s} from {spec}')
                getattr(pst, f'add_{t}')(table(spec, t))
    if args.fill_parval:
        if manifest is not None:
            manifest.add_source(args.fill_parval, role='parval')
        pst.fill_parval(args.fill_parval, args.real)
    return pst


def _version(args):
    return 2 if getattr(args, 'v2', False) else 1 if getattr(args, 'v1', False) else None


def _finish_pst(pst, path, manifest, dump_tpl, version=None):
    write_pst(pst, path, dump_tpl=dump_tpl, version=version)
    if manifest is not None:
        manifest.set_output(path, **pst.counts)
        print(f'manifest written to {manifest.write()}')


def build(args):
    manifest = None if args.no_manifest else Manifest('build', args._argv)
    if args.pstfile.lower().endswith(WORKBOOK_EXT):
        # `makepst build book.xlsx [--out x.pst]`: run the command in the workbook's BUILD sheet
        pst, ns = build_from_workbook(args.pstfile, manifest)
        out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.pstfile)), ns.pstfile)
        _finish_pst(pst, out, manifest, dump_tpl=not (args.no_dump_tpl or ns.no_dump_tpl),
                    version=_version(args) or _version(ns))
        return
    pst = build_pst(args, manifest)
    _finish_pst(pst, args.pstfile, manifest, dump_tpl=not args.no_dump_tpl, version=_version(args))


def build_from_workbook(book, manifest=None):
    """The Pst a workbook describes in its BUILD sheet (the command `dump` records there),
    with the parsed build arguments; returns (pst, args)."""
    import pandas as pd
    try:
        rows = pd.read_excel(book, 'BUILD', engine='openpyxl').iloc[:, 0].dropna()
    except ValueError:
        raise SystemExit(f'{book} has no BUILD sheet; add one holding the build command '
                         f'(as `makepst dump` does), or use `makepst build ... --fill_parval`') from None
    argv = [a.strip('"') for a in shlex.split(' '.join(str(r) for r in rows), posix=False)]
    while argv and (argv[0].lower() in ('python', 'makepst', 'build') or argv[0].lower().endswith('makepst.py')):
        argv.pop(0)
    argv = _resolve_paths(argv, book)
    parser = argparse.ArgumentParser(prog='BUILD sheet')
    _build_parser(parser)
    ns = parser.parse_args(argv)
    if manifest is not None:
        manifest.add_source(book, 'BUILD', 'build command')
        manifest.add(build_args=argv)      # resolved paths, as executed
    return build_pst(ns, manifest), ns


def _resolve_paths(argv, book):
    """Make the file names in a BUILD command usable from anywhere: the workbook's own name means
    this workbook, other relative names are taken relative to the workbook's folder."""
    base = os.path.dirname(os.path.abspath(book))
    out = []
    for a in argv:
        path, sep, sheet = a.rpartition(',')
        if not sep:
            path, sheet = a, ''
        if os.path.basename(path).lower() == os.path.basename(book).lower():
            path = book
        elif not os.path.isabs(path) and os.path.exists(os.path.join(base, path)) and not os.path.exists(path):
            path = os.path.join(base, path)
        out.append(path + sep + sheet)
    return out


def dump(args):
    pst = read_pst(args.pstfile)
    cmd = to_workbook(pst, args.workbook, split=args.split)
    print('rebuild with:\n  ' + cmd)
    if not args.no_manifest:
        m = Manifest('dump', args._argv)
        m.add_source(args.pstfile, role='control file')
        m.set_output(args.workbook, **pst.counts)
        m.add(build_command=cmd)
        print(f'manifest written to {m.write()}')


def init(args):
    from .starter import write_starter
    if os.path.exists(args.workbook) and not args.force:
        raise SystemExit(f'{args.workbook} exists; use --force to overwrite')
    cmd = write_starter(args.workbook, args.name)
    print(f'starter workbook written to {args.workbook}')
    print(f'build it with:\n  {cmd}')


def parrep(args):
    """PARREP: parameter values from a .par file (or IES ensemble) into a control file.

    The base is a control file, or a workbook with a BUILD sheet (built first, then filled).
    """
    manifest = None if args.no_manifest else Manifest('parrep', args._argv)
    if args.pstfile.lower().endswith(WORKBOOK_EXT):
        pst, _ = build_from_workbook(args.pstfile, manifest)
    else:
        pst = read_pst(args.pstfile)
        if manifest is not None:
            manifest.add_source(args.pstfile, role='base control file')
    if manifest is not None:
        manifest.add_source(args.parfile, role='parameter values')
        manifest.add(realization=args.real, set=args.set)
    pst.fill_parval(args.parfile, args.real)
    for kv in args.set:
        k, _, v = kv.partition('=')
        if not _:
            raise SystemExit(f'--set expects NAME=VALUE, got {kv!r}')
        pst.set_control({k: v})
    _finish_pst(pst, args.out, manifest, dump_tpl=False, version=_version(args))


def validate(args):
    """pestchek-style report for a control file or a workbook (built via its BUILD sheet)."""
    from .checks import summary, validate as run_checks
    target = args.target
    if target.lower().endswith(WORKBOOK_EXT):
        pst, _ = build_from_workbook(target)
        pst_path = None
    else:
        pst = read_pst(target)
        pst_path = target
    base = args.base_dir or os.path.dirname(os.path.abspath(target))
    findings = run_checks(pst, base_dir=base, pst_path=pst_path, outputs=args.outputs)
    order = {'error': 0, 'warning': 1, 'info': 2}
    for f in sorted(findings, key=lambda f: order[f.severity]):
        if f.severity == 'info' and args.quiet:
            continue
        print(f)
    n, text = summary(findings)
    print(f'{target}: {text}')
    if n['error'] or (args.strict and n['warning']):
        raise SystemExit(1)


def _load_target(path):
    """A control file or a workbook (built via its BUILD sheet) -> Pst."""
    if path.lower().endswith(WORKBOOK_EXT):
        return build_from_workbook(path)[0]
    return read_pst(path)


def diff(args):
    """Semantic comparison of two control files / workbooks; exit 1 when they differ."""
    from .diff import compare
    old, new = _load_target(args.old), _load_target(args.new)
    old.validate()
    new.validate()
    d = compare(old, new, rtol=args.rtol)
    print(d.to_text(max_rows=args.max_rows))
    print(f'{args.old} -> {args.new}: {d.summary()}')
    if args.xlsx:
        d.to_workbook(args.xlsx)
        print(f'written to {args.xlsx}')
    if not d.empty:
        raise SystemExit(1)


def update(args):
    pst = read_pst(args.pst) if args.pst else None
    par = args.par or pst
    if args.par and pst is not None:
        # .par values with the groups from the pst, so --group can apply to them
        par = (read_par(args.par, args.real).reset_index()
               .merge(pst.par[['PARNME', 'PARGP']], on='PARNME', how='left'))

    def flat(items):   # repeated flags, each possibly a comma list
        return [x.strip() for s in items for x in s.split(',') if x.strip()] or None

    manifest = None if args.no_manifest else Manifest('update', args._argv)
    if manifest is not None:
        manifest.add_source(args.workbook, role='workbook')
        for path, role in ((args.par, 'parameter values'), (args.pst, 'control file'),
                           (args.res, 'residuals'), (args.obs_csv, 'observation ensemble')):
            if path:
                manifest.add_source(path, role=role)
    result = update_workbook(args.workbook, par=par, obs=pst, res=args.res, obs_csv=args.obs_csv,
                             real=args.real, pst=pst, out=args.out, backend=args.backend,
                             par_cols=args.par_cols.upper().split(','), obs_cols=args.obs_cols.upper().split(','),
                             overwrite_formulas=args.overwrite_formulas,
                             sheets=flat(args.sheet), groups=flat(args.group), phi=not args.no_phi)
    if manifest is not None:
        manifest.set_output(args.out or args.workbook, sheets=result['sheets'], backend=result['backend'])
        manifest.add(realization=args.real, par_cols=args.par_cols, obs_cols=args.obs_cols,
                     sheet=flat(args.sheet), group=flat(args.group), overwrite_formulas=args.overwrite_formulas)
        print(f'manifest written to {manifest.write()}')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # legacy form: makePst.py out.pst mode --add_par_xls ...  (no subcommand)
    if argv and argv[0] not in ('build', 'dump', 'update', 'parrep', 'init', 'validate', 'diff', '-h', '--help', '-v', '--version'):
        argv.insert(0, 'build')

    ap = argparse.ArgumentParser(prog='makepst', description=__doc__)
    ap.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    sub = ap.add_subparsers(dest='cmd', required=True)

    _build_parser(sub.add_parser('build', help='Excel/CSV tables -> PEST control file'))

    d = sub.add_parser('dump', help='PEST control file -> new workbook')
    d.add_argument('pstfile')
    d.add_argument('workbook', help='.xlsx to create')
    d.add_argument('--split', action='store_true', help='one PAR_<group> / OBS_<group> sheet per group')
    d.add_argument('--no_manifest', action='store_true', help="don't write <workbook>.manifest.json")

    i = sub.add_parser('init', help='starter workbook with headers, defaults, drop-downs and a BUILD sheet')
    i.add_argument('workbook', help='.xlsx to create')
    i.add_argument('--name', help='case name for the control file in the BUILD command (default: workbook name)')
    i.add_argument('--force', action='store_true', help='overwrite an existing file')

    r = sub.add_parser('parrep', help='new control file with parameter values from a .par file (like PARREP)')
    r.add_argument('pstfile', help='control file to read, or a workbook with a BUILD sheet to build it from')
    r.add_argument('parfile', help='PEST .par file or PESTPP-IES case.N.par.csv')
    r.add_argument('out', help='control file to write')
    r.add_argument('--real', metavar='NAME', help='realization for an ensemble (base, 17, best; default base)')
    r.add_argument('--set', action='append', default=[], metavar='NAME=VALUE',
                   help='also change a control value, e.g. --set noptmax=0 (repeatable)')
    r.add_argument('--no_manifest', action='store_true', help="don't write <out>.manifest.json")
    rf = r.add_mutually_exclusive_group()
    rf.add_argument('--v2', action='store_true', help='write a PEST++ version-2 file')
    rf.add_argument('--v1', action='store_true', help='write the classic format (default: same as the input)')

    v = sub.add_parser('validate', help='pestchek-style checks on a control file or a workbook')
    v.add_argument('target', help='control file, or a workbook with a BUILD sheet')
    v.add_argument('--outputs', action='store_true',
                   help='also run each instruction file against its model output file when that exists')
    v.add_argument('--base_dir', metavar='DIR', help='folder template/instruction paths are relative to '
                                                     '(default: the folder of the target)')
    v.add_argument('--strict', action='store_true', help='exit 1 on warnings as well as errors')
    v.add_argument('--quiet', action='store_true', help='hide informational lines')

    f = sub.add_parser('diff', help='what changed between two control files (or workbooks)')
    f.add_argument('old', help='control file or workbook')
    f.add_argument('new', help='control file or workbook')
    f.add_argument('--xlsx', metavar='FILE', help='also write the differences to a workbook, one sheet per table')
    f.add_argument('--rtol', type=float, default=1e-9, help='relative tolerance for numbers (default 1e-9)')
    f.add_argument('--max_rows', type=int, default=50, help='rows printed per table (default 50)')

    u = sub.add_parser('update', help='write PEST results back into an existing workbook')
    u.add_argument('workbook', help='.xlsm/.xlsx to update (sheets matched by PARNME / OBSNME columns)')
    u.add_argument('--par', metavar='FILE', help='PEST .par file or PESTPP-IES case.N.par.csv -> PARVAL1')
    u.add_argument('--pst', metavar='PSTFILE', help='control file -> parameter and observation columns')
    u.add_argument('--res', metavar='RESFILE', help='PEST .res/.rei -> MODELLED / RESIDUAL columns')
    u.add_argument('--obs_csv', metavar='FILE',
                   help='PESTPP-IES case.N.obs.csv -> MODELLED (and RESIDUAL when --pst is given)')
    u.add_argument('--real', metavar='NAME',
                   help='realization to take from IES ensembles: a name such as base or 17, '
                        'or best (lowest phi in case.phi.actual.csv); default base')
    u.add_argument('--par_cols', default='PARVAL1', help='comma list of parameter columns to write')
    u.add_argument('--obs_cols', default='OBSVAL,WEIGHT', help='comma list of observation columns to write')
    u.add_argument('--sheet', action='append', default=[], metavar='GLOB',
                   help='only worksheets matching this name pattern, e.g. PAR_HK or "OBS_*" (repeatable, or a comma list)')
    u.add_argument('--group', action='append', default=[], metavar='NAME',
                   help='only parameters/observations in this group (repeatable, or a comma list; '
                        'with --par alone, also give --pst)')
    u.add_argument('--overwrite_formulas', action='store_true',
                   help='also write into cells that currently hold formulas (default: leave them alone)')
    u.add_argument('--out', help='save to this file instead of in place')
    u.add_argument('--backend', choices=['xlwings', 'openpyxl'], help='default: xlwings if installed')
    u.add_argument('--no_manifest', action='store_true', help="don't write <workbook>.manifest.json")
    u.add_argument('--no_phi', action='store_true', help="don't write the PHI / PHI_IES sheets with --res / --obs_csv")

    args = ap.parse_args(argv)
    args._argv = argv                 # the command line as given, for the manifest
    {'build': build, 'dump': dump, 'update': update, 'parrep': parrep, 'init': init,
     'validate': validate, 'diff': diff}[args.cmd](args)


if __name__ == '__main__':
    main()
