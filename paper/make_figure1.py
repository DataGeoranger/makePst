"""Write paper/figure1.svg, the workflow figure of the manuscript.

    python paper/make_figure1.py            # writes figure1.svg next to this script
    python paper/make_figure1.py out.svg    # or elsewhere

Plain SVG, no dependencies. White background (never rely on transparency), no caption inside
the graphic (the manuscript carries it), grayscale-safe. For the journal's raster/PDF formats
convert with Inkscape (inkscape figure1.svg --export-type=pdf) or cairosvg.
"""
import os
import sys

W, H = 1060, 600

STYLE = """
    .box { fill: #fff; stroke: #222; stroke-width: 1.6; }
    .hub { fill: #e6e6e6; stroke: #222; stroke-width: 2; }
    .file { fill: #f7f7f7; stroke: #555; stroke-width: 1.2; stroke-dasharray: 5 3; }
    .banner { fill: #f2f2f2; stroke: #222; stroke-width: 1.2; }
    .h { fill: #111; font-weight: bold; font-size: 17px; }
    .c { fill: #111; font-family: Menlo, Consolas, monospace; font-size: 14px; font-weight: bold; }
    .s { fill: #333; font-size: 13.5px; }
    .a { stroke: #222; stroke-width: 1.7; fill: none; marker-end: url(#arrow); }
    .a2 { stroke: #222; stroke-width: 1.7; fill: none; marker-end: url(#arrow); marker-start: url(#arrow); }
"""


def text(x, y, s, cls='s', anchor='middle'):
    return f'  <text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}">{s}</text>\n'


def box(x, y, w, h, title, lines, cls='box', rx=8):
    out = f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}"/>\n'
    cx = x + w / 2
    out += text(cx, y + 33, title, 'h')
    for i, ln in enumerate(lines):
        out += text(cx, y + 58 + 19 * i, ln)
    return out


def arrow(d, both=False, dashed=False):
    dash = ' stroke-dasharray="6 4"' if dashed else ''
    return f'  <path d="{d}" class="{"a2" if both else "a"}"{dash}/>\n'


def figure():
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         'font-family="Helvetica, Arial, sans-serif" font-size="15">\n'
         '  <defs>\n'
         '    <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="strokeWidth">\n'
         '      <path d="M0,0 L10,5 L0,10 z" fill="#222"/>\n'
         '    </marker>\n'
         '  </defs>\n'
         f'  <style>{STYLE}  </style>\n\n'
         '  <!-- white background: never rely on the viewer\'s transparency handling -->\n'
         f'  <rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>\n\n')

    # diff: comparison of any two configurations
    s += '  <!-- diff: comparison of any two configurations -->\n'
    s += arrow('M150,170 C150,118 850,118 850,170', both=True)
    s += text(500, 84, 'diff', 'c') + text(500, 102, 'semantic comparison of configurations')

    # main flow: workbook <-> makePst <-> control file
    s += '\n  <!-- main flow -->\n'
    s += box(40, 170, 220, 110, 'Calibration workbook',
             ['Excel or CSV tables', 'formulas and helper columns kept', 'reviewed project record'])
    s += (f'  <rect x="400" y="180" width="200" height="90" rx="45" class="hub"/>\n'
          + text(500, 216, 'makePst', 'h') + text(500, 238, 'structured data +') + text(500, 255, 'consistency checks'))
    s += box(740, 170, 220, 110, 'PEST control file',
             ['PEST · PEST_HP · PEST++', 'classic or version-2 format', 'counts computed, priors generated'])
    s += arrow('M260,208 L400,208') + text(330, 199, 'build', 'c')
    s += arrow('M400,244 L260,244') + text(330, 265, 'dump', 'c')
    s += arrow('M600,208 L740,208') + text(670, 199, 'write', 'c')
    s += arrow('M740,244 L600,244') + text(670, 265, 'read', 'c')

    # model interface + validate
    s += '\n  <!-- model interface + validate -->\n'
    s += box(400, 370, 200, 72, 'Model interface', ['templates · instructions · model output'], cls='file')
    s += arrow('M500,270 L500,370', both=True)
    s += text(512, 316, 'validate', 'c', 'start') + text(512, 334, 'consistency and interface checks', anchor='start')

    # PEST run, results, parrep
    s += '\n  <!-- PEST run + results -->\n'
    s += box(740, 370, 220, 72, 'PEST / PEST++ run', ['parameter · residual · ensemble results'], cls='file')
    s += arrow('M810,280 L810,370') + text(798, 330, 'run', anchor='end')
    s += arrow('M890,370 L890,280', dashed=True)
    s += (text(902, 318, 'parrep', 'c', 'start') + text(902, 336, 'selected values →', anchor='start')
          + text(902, 352, 'new control file', anchor='start'))

    # update: results back to the workbook
    s += '\n  <!-- update: results back to the workbook -->\n'
    s += arrow('M740,415 C560,500 300,500 150,280')
    s += text(430, 492, 'update', 'c') + text(430, 510, 'results returned by name; formulas preserved')

    # provenance banner: cross-cutting
    s += '\n  <!-- provenance banner -->\n'
    s += f'  <rect x="40" y="540" width="{W - 80}" height="40" rx="6" class="banner"/>\n'
    s += text(60, 565, 'provenance manifest', 'c', 'start')
    s += text(250, 565, 'with every produced file: software version · command · input and output hashes · project dimensions',
              anchor='start')
    return s + '</svg>\n'


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figure1.svg')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(figure())
    print('written', out)
