# P-B — Selected XLSX Sheet with Cached Formula Values

## Test order

Read exactly the `Orders` sheet. Cells F2:F5 contain formulas with stored cached values.
Pilot emits `XLSX_FORMULA_PRESENT`, reads the cached numbers, does not recalculate formulas,
deduplicates by order_id and exports values only.

## Exact expected result

`expected_result.xlsx` and `expected_result.csv` contain three rows and the exact Unicode headers:
`Номер заказа, Товар, Количество, Цена за единицу, Дата заказа, Сумма строки`.
The output workbook contains no formula elements.

## Formula error case

`formula_detection_cases.json` fixes `XLSX_FORMULA_CACHE_MISSING` as a fatal ingestion error when
a selected-sheet formula cell has no cached value.
