# Pilot Ingestion and Output Header Rules

## CSV ingestion

- Allowed encodings: `UTF-8`, `UTF-8-SIG`, `CP1251`.
- Allowed delimiters: comma `,`, semicolon `;`, tab `\t`.
- Encoding and delimiter are selected explicitly by the user and stored in
  `TransformationSpecVersion.inputs[0].csv_options`.
- Automatic detection, trial decoding and hidden fallback are forbidden.
- A decode or parse failure produces `INPUT_UNREADABLE` and the execution state `FAILED`.
- After successful reading, the UI must display the detected technical schema and the first
  five data rows before the specification is approved/executed.

## Date parsing

The closed format list is:

- `YYYY-MM-DD`
- `DD.MM.YYYY`
- `DD/MM/YYYY`
- `MM/DD/YYYY`
- `YYYY/MM/DD`
- `YYYY-MM-DD HH:mm:ss`
- `DD.MM.YYYY HH:mm:ss`

Every `parse_date` operation contains an explicit ordered `formats` list. `DD/MM/YYYY` and
`MM/DD/YYYY` cannot appear together in one operation. No locale inference or day/month guessing
is permitted.

## XLSX formulas

- Pilot does not execute or recalculate formulas.
- Source formula cells are read only through stored cached values.
- Every formula cell produces the warning code `XLSX_FORMULA_PRESENT` once per input asset,
  with affected cell count and a bounded cell-address sample.
- If any selected-sheet formula lacks a cached value, reading stops with
  `XLSX_FORMULA_CACHE_MISSING`; no partial dataset is created.
- The user must recalculate and save the workbook in an external spreadsheet editor.
- Pilot XLSX export contains values only and no formula elements.

## Internal names and output headers

- `name` is the internal technical identifier and matches `^[A-Za-z_][A-Za-z0-9_]{0,127}$`.
- `output_name` is the actual CSV/XLSX header.
- Before persistence, `output_name` is trimmed and normalized to Unicode NFC.
- Its normalized length is 1–128 characters.
- Unicode control characters, tab, carriage return and line feed are forbidden.
- Normalized `output_name` values are unique in the final schema.
- UI/defaulting logic sets `output_name=name`; the stored version materializes the value.
- Operations and `column_order` reference internal `name`; export maps to `output_name`.
