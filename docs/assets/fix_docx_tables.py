import sys
from docx import Document
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

path = sys.argv[1]
doc = Document(path)
TOTAL = 6.5  # inches of text width on US Letter with 1" margins
for t in doc.tables:
    ncol = len(t.rows[0].cells)
    lens = [0] * ncol
    for r in t.rows:
        for i, c in enumerate(r.cells):
            lens[i] = max(lens[i], min(len(c.text), 60))
    w = [max(l, 6) ** 0.8 for l in lens]
    s = sum(w)
    widths = [TOTAL * x / s for x in w]
    t.autofit = False
    tblPr = t._tbl.tblPr
    for el in tblPr.findall(qn('w:tblW')):
        tblPr.remove(el)
    tw = OxmlElement('w:tblW'); tw.set(qn('w:w'), str(int(TOTAL * 1440))); tw.set(qn('w:type'), 'dxa'); tblPr.append(tw)
    lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblPr.append(lay)
    borders = OxmlElement('w:tblBorders')
    for side in ('top', 'bottom', 'insideH'):
        b = OxmlElement(f'w:{side}'); b.set(qn('w:val'), 'single'); b.set(qn('w:sz'), '4'); b.set(qn('w:color'), '808080'); borders.append(b)
    tblPr.append(borders)
    grid = t._tbl.find(qn('w:tblGrid'))
    for g in list(grid):
        grid.remove(g)
    for x in widths:
        gc = OxmlElement('w:gridCol'); gc.set(qn('w:w'), str(int(x * 1440))); grid.append(gc)
    for r in t.rows:
        for i, c in enumerate(r.cells):
            c.width = Inches(widths[i])
            for p in c.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
doc.save(path)
print('fixed', len(doc.tables), 'tables')
