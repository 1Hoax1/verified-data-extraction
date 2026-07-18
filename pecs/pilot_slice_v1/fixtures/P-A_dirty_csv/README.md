# P-A — Dirty CP1251 CSV

## Test order

The user explicitly selects `CP1251` and comma delimiter. The preview must show the decoded
schema and first five rows before approval. The pipeline normalizes values, parses dates/numbers,
fills blank revenue, drops the blank-name row, deduplicates email and exports UTF-8 CSV.

The internal technical fields remain ASCII identifiers. The exact exported headers are:
`Имя клиента, Страна, Дата регистрации, Выручка, Статус, Email`.

## Exact expected result

`expected_result.csv` contains exactly three rows: Алиса Смит, Bob Jones, Carla Ruiz.

## Failure assertion

A wrong explicitly selected encoding produces `INPUT_UNREADABLE`; no detection/fallback occurs.
