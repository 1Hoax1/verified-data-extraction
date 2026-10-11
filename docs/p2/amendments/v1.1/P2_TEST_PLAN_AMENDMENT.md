# P2 Test Plan amendment v1.1 — CR-P3-002

Authority: [approved CR-P3-002](../../../change_requests/CR-P3-002.md) and [P3 implementation start](../../../p3/v1.0/IMPLEMENTATION_START_AUTHORIZATION.md).

P2-T40 retains its ID, dependency checks, migration/P1 integrity checks and every original negative probe. Its historical runtime scope is the explicit P1 inventory plus all validated P2 ingestion modules, frozen by SHA-256. Only the approved P3 workflow paths and necessary `app.py` integration are authorized additions. The app integration retains exact reviewed import/call/definition checks. Branch change auditing uses authorized main `ba73d05d2294dfb7e51b9c3c758e63c6065286d6`, excluding already approved upstream governance changes.

P3-T51 audits the complete application inventory, reviewed P3 source hashes/surfaces, unchanged dependencies/lock graph, frozen P1/P2 source and migration, actual SQLite table inventory, forbidden integrations/execution and negative probes. No test is removed, skipped or xfailed. P1/P2 runtime and original P2 Pack v1.0 are unchanged.
