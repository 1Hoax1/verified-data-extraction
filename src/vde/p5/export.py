"""Single approved-format staging; strings never become spreadsheet formulas."""
import csv
from datetime import date, datetime, time
from decimal import Decimal
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from .errors import P5Error, require
from .project import csv_cell, safe_csv_string, numeric_preflight


def text_cell(sheet, text):
    # Force the actual OpenXML cell type after assignment, including '=...'.
    require(len(text) <= 32767, 'EXPORT_FAILED', 'XLSX text exceeds cell capacity')
    cell = WriteOnlyCell(sheet, value=text)
    cell.data_type = 's'
    return cell


def xlsx_value(sheet, value):
    if type(value) is str:
        return text_cell(sheet, value)
    if type(value) in (int, Decimal):
        numeric_preflight(value)
        return value
    if value is None or type(value) is bool:
        return value
    if type(value) in (date, datetime, time):
        # ISO text is the approved date format, not an implicit Excel serial.
        return text_cell(sheet, value.isoformat().replace('+00:00', 'Z'))
    raise P5Error('EXPORT_FAILED', 'Unsupported XLSX scalar')


def write(path, projection, rows, budget, observe=lambda row: None):
    output, count = projection.output, 0
    try:
        if output['format'] == 'CSV':
            require(output['encoding'] == 'UTF-8' and output['delimiter'] in (',', ';', '\t'),
                    'EXPORT_FAILED', 'Unsupported approved CSV dialect')
            with path.open('x', encoding='utf-8', errors='strict', newline='') as stream:
                writer = csv.writer(stream, delimiter=output['delimiter'], lineterminator='\n')
                writer.writerow([safe_csv_string(s) for s in projection.headers])
                for count, row in enumerate(rows, 1):
                    require(len(row) == len(projection.columns) and count <= 100000,
                            'SCHEMA_MISMATCH', 'Export row shape exceeds Pilot')
                    writer.writerow([csv_cell(v) for v in row])
                    observe(row)
                    if count % 100 == 0:
                        budget.check()
                        require(stream.tell() <= budget.limit, 'EXPORT_FAILED', 'Output exceeds bounded P1 bytes capacity')
                stream.flush()
        else:
            workbook = Workbook(write_only=True)
            sheet = workbook.create_sheet(output['sheet_name'])
            try:
                sheet.append([text_cell(sheet, h) for h in projection.headers])
                for count, row in enumerate(rows, 1):
                    require(len(row) == len(projection.columns) and count <= 100000,
                            'SCHEMA_MISMATCH', 'Export row shape exceeds Pilot')
                    sheet.append([xlsx_value(sheet, value) for value in row])
                    observe(row)
                    if count % 100 == 0:
                        budget.check()
                workbook.save(path)
            finally:
                # Close write-only generators on failed staging too.
                if not sheet.closed:
                    sheet.close()
                workbook.close()
        budget.check()
        return count
    except P5Error:
        raise
    except (OSError, ValueError, TypeError, UnicodeError, OverflowError) as exc:
        raise P5Error('EXPORT_FAILED', 'Writer could not produce faithful output') from exc
