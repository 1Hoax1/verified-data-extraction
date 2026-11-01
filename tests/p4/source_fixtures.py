"""Test-only typed source construction for executing approved F tables via P3."""
import io
import zipfile
from xml.etree import ElementTree as ET

from openpyxl import Workbook
from openpyxl.utils.cell import get_column_letter, coordinate_to_tuple


def cached_xlsx(columns, rows):
    book = Workbook()
    sheet = book.active
    sheet.title = 'Orders'
    sheet.append(columns)
    for row in rows:
        sheet.append(row)
    output = io.BytesIO()
    book.save(output)
    book.close()
    # OOXML/openpyxl otherwise collapses a literal zero-length inline string
    # to None. An explicit, manually seeded empty cached string is a supported
    # frozen P2 representation and preserves the fixture's exact input type.
    empty = {(r+2, c+1) for r, row in enumerate(rows) for c, value in enumerate(row) if value == '' and type(value) is str}
    if not empty:
        return output.getvalue()
    fixed = io.BytesIO()
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    with zipfile.ZipFile(output) as original, zipfile.ZipFile(fixed, 'w', zipfile.ZIP_STORED) as target:
        for entry in original.infolist():
            data = original.read(entry.filename)
            if entry.filename == 'xl/worksheets/sheet1.xml':
                tree = ET.fromstring(data)
                for row_number, col_number in sorted(empty):
                    row = next(e for e in tree.iter(ns+'row') if e.get('r') == str(row_number))
                    coordinate = get_column_letter(col_number)+str(row_number)
                    cell = next((c for c in row if c.get('r') == coordinate), None)
                    if cell is None:
                        cell = ET.Element(ns+'c')
                        position = sum(coordinate_to_tuple(c.get('r'))[1] < col_number for c in row)
                        row.insert(position, cell)
                    cell.clear()
                    cell.set('r', coordinate)
                    cell.set('t', 'str')
                    ET.SubElement(cell, ns+'f').text = '""'
                    ET.SubElement(cell, ns+'v')
                data = ET.tostring(tree)
            target.writestr(entry.filename, data)
    return fixed.getvalue()
