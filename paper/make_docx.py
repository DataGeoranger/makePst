"""manuscript.md -> manuscript.docx, laid out for submission.

Run: python paper/make_docx.py [--out FILE] [--no_line_numbers] [--keep_notes]

pandoc converts the Markdown (headings, emphasis, inline code, the table, links); this script
then sets the manuscript style Word-side: US Letter, 1-inch margins, Times New Roman 12 pt,
double spacing, continuous line numbers, the table single-spaced with a grid, the title
centred, the figure (figure1.png) placed above its caption on a page of its own at the end.
The draft/target line and the bracketed production notes ([Figure file: ...], [confirm at
submission] ...) are dropped, as they would be at submission; --keep_notes keeps them. Notes
that still need the author ([date], acknowledgments) stay either way. Needs pandoc on the
PATH and python-docx.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, 'manuscript.md')
FIGURE = os.path.join(HERE, 'figure1.png')
FONT, MONO = 'Times New Roman', 'Consolas'
TABLE_WIDTHS = {4: (1.7, 2.2, 0.6, 2.0)}                # Table 1: Step / Command / Time / Result, inches


def strip_notes(text):
    """Remove the bracketed editorial notes ([To be filled ...], [Figure file: ...]) and the draft line."""
    text = re.sub(r'^\*Technology Spotlight[^\n]*\n', '', text, flags=re.M)     # the draft/target line
    production = ('To be filled', 'Figure file', 'confirm at submission', 're-count')
    text = re.sub(r' ?\[(?!\^)[^\[\]\n]*\]',
                  lambda m: '' if any(w in m.group(0) for w in production) else m.group(0), text)
    return text


def pandoc(md_text, out):
    if shutil.which('pandoc') is None:
        sys.exit('pandoc not found on the PATH (conda install pandoc, or https://pandoc.org)')
    subprocess.run(['pandoc', '-f', 'markdown+smart+hard_line_breaks', '-t', 'docx', '-o', out],
                   input=md_text.encode('utf-8'), check=True)


def set_fonts(doc):
    for style in doc.styles:
        if style.type != 1:                                   # paragraph styles only
            continue
        try:
            style.font.name = FONT
            rpr = style.element.get_or_add_rPr()
            fonts = rpr.find(qn('w:rFonts'))
            if fonts is None:
                fonts = OxmlElement('w:rFonts')
                rpr.append(fonts)
            for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
                fonts.set(qn(attr), FONT)
            for attr in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
                fonts.attrib.pop(qn(attr), None)              # theme fonts would override the name
        except AttributeError:
            pass
    names = [s.name for s in doc.styles]
    for name in ('Normal', 'Body Text', 'First Paragraph', 'Compact'):     # pandoc's body styles
        if name in names:
            st = doc.styles[name]
            st.font.size = Pt(12)
            st.paragraph_format.line_spacing = 2.0
            st.paragraph_format.space_before = Pt(0)
            st.paragraph_format.space_after = Pt(0)
            st.paragraph_format.first_line_indent = None
    for name, size in (('Heading 1', 14), ('Heading 2', 12), ('Heading 3', 12), ('Title', 14)):
        if name in [s.name for s in doc.styles]:
            st = doc.styles[name]
            st.font.size, st.font.bold, st.font.italic = Pt(size), True, False
            st.font.color.rgb = None
            st.paragraph_format.line_spacing = 2.0
            st.paragraph_format.space_before = Pt(12 if name != 'Heading 1' else 0)
            st.paragraph_format.space_after = Pt(0)
            st.paragraph_format.keep_with_next = True
    for name in ('Verbatim Char', 'Source Code'):
        if name in [s.name for s in doc.styles]:
            st = doc.styles[name]
            st.font.name = MONO
            st.font.size = Pt(10.5)
            rpr = st.element.get_or_add_rPr()
            fonts = rpr.find(qn('w:rFonts'))
            if fonts is not None:
                for attr in ('w:ascii', 'w:hAnsi', 'w:cs'):
                    fonts.set(qn(attr), MONO)


def page_setup(doc, line_numbers=True):
    for section in doc.sections:
        section.page_width, section.page_height = Inches(8.5), Inches(11)
        for side in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
            setattr(section, side, Inches(1))
        sect = section._sectPr
        for old in sect.findall(qn('w:lnNumType')):
            sect.remove(old)
        if line_numbers:
            ln = OxmlElement('w:lnNumType')
            ln.set(qn('w:countBy'), '1')
            ln.set(qn('w:restart'), 'continuous')
            ln.set(qn('w:distance'), '360')
            pgsz = sect.find(qn('w:pgSz'))
            (pgsz.addprevious if pgsz is not None else sect.append)(ln)
        # page numbers in the footer
        footer = section.footer
        p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
        run = p.add_run()
        for tag, text in (('begin', None), (None, 'PAGE'), ('end', None)):
            if tag:
                el = OxmlElement('w:fldChar')
                el.set(qn('w:fldCharType'), tag)
            else:
                el = OxmlElement('w:instrText')
                el.set(qn('xml:space'), 'preserve')
                el.text = text
            run._r.append(el)


def style_title(doc):
    """The first paragraph (pandoc: Heading 1 or Title) centred; author lines centred too."""
    paras = doc.paragraphs
    if not paras:
        return
    paras[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for p in paras[1:3]:                                      # authors, affiliation
        if p.style.name.startswith('Heading') or p.text.startswith('Article Impact'):
            break
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _borders(table):
    tbl_pr = table._tbl.tblPr
    for old in tbl_pr.findall(qn('w:tblBorders')):
        tbl_pr.remove(old)
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), '4')
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), '000000')
        borders.append(el)
    tbl_pr.append(borders)


def _column_widths(table, inches):
    """Fixed column widths: the grid, the table width and every cell (pandoc writes a percentage grid)."""
    twips = [int(w * 1440) for w in inches]
    tbl = table._tbl
    grid = tbl.find(qn('w:tblGrid'))
    if grid is not None:
        for col, w in zip(grid.findall(qn('w:gridCol')), twips):
            col.set(qn('w:w'), str(w))
    tbl_pr = tbl.tblPr
    for tag in ('w:tblW', 'w:tblLayout'):
        for old in tbl_pr.findall(qn(tag)):
            tbl_pr.remove(old)
    tw = OxmlElement('w:tblW')
    tw.set(qn('w:w'), str(sum(twips)))
    tw.set(qn('w:type'), 'dxa')
    layout = OxmlElement('w:tblLayout')
    layout.set(qn('w:type'), 'fixed')
    tbl_pr.append(tw)
    tbl_pr.append(layout)
    for row in table.rows:
        for cell, w in zip(row.cells, inches):
            cell.width = Inches(w)


def style_tables(doc):
    for table in doc.tables:
        _borders(table)                                   # pandoc's docx has no bordered table style
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        widths = TABLE_WIDTHS.get(len(table.columns))
        if widths:
            _column_widths(table, widths)
        for i, row in enumerate(table.rows):
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.line_spacing = 1.0
                    p.paragraph_format.space_after = Pt(2)
                    for r in p.runs:
                        r.font.size = Pt(10)
                        if i == 0:
                            r.font.bold = True
        # the caption paragraph ("Table 1. ...") sits just before the table: keep it with the table
        prev = table._tbl.getprevious()
        if prev is not None and prev.tag == qn('w:p'):
            for p in doc.paragraphs:
                if p._p is prev:
                    p.paragraph_format.keep_with_next = True
                    p.paragraph_format.line_spacing = 1.0
                    p.paragraph_format.space_before = Pt(12)
                    p.paragraph_format.space_after = Pt(6)


def place_figure(doc, figure):
    """The figure above its caption, on a page of its own after the references."""
    caption = next((p for p in doc.paragraphs if p.text.startswith('Figure 1.')), None)
    if caption is None:
        print('no "Figure 1." caption paragraph found; figure not placed')
        return
    # drop the horizontal rule pandoc put before the caption (an empty bordered paragraph)
    prev = caption._p.getprevious()
    if prev is not None and prev.tag == qn('w:p') and not ''.join(prev.itertext()).strip():
        prev.getparent().remove(prev)
    holder = caption.insert_paragraph_before()
    holder.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = holder.add_run()
    run.add_break(WD_BREAK.PAGE)
    if os.path.exists(figure):
        run.add_picture(figure, width=Inches(6.5))
    else:
        print(f'{figure} not found; a page break was left where the figure goes')
    holder.paragraph_format.keep_with_next = True
    caption.paragraph_format.line_spacing = 1.0
    caption.paragraph_format.space_before = Pt(6)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=os.path.join(HERE, 'manuscript.docx'))
    ap.add_argument('--no_line_numbers', action='store_true')
    ap.add_argument('--keep_notes', action='store_true', help='keep the bracketed editorial notes and the draft line')
    args = ap.parse_args(argv)

    text = open(MD, encoding='utf-8').read()
    if not args.keep_notes:
        text = strip_notes(text)
    pandoc(text, args.out)

    doc = Document(args.out)
    set_fonts(doc)
    page_setup(doc, line_numbers=not args.no_line_numbers)
    style_title(doc)
    style_tables(doc)
    place_figure(doc, FIGURE)
    doc.save(args.out)
    words = len(re.findall(r"[A-Za-z0-9'’\-]+", '\n'.join(p.text for p in doc.paragraphs)))
    print(f'{args.out}: {len(doc.paragraphs)} paragraphs, {len(doc.tables)} table(s), ~{words} words')


if __name__ == '__main__':
    main()
