# P4 canonical Decimal amendment v1.2 — approved CR-P4-004

Owner-approved 2026-10-30. This corrects the claimed equivalent regex in the immutable v1.0 handoff document without replacing its archive.

Canonical finite Decimal text, whole-string ASCII:

`(?:0|-?(?:[1-9][0-9]*(?:\.[0-9]*[1-9])?|0\.[0-9]*[1-9]))`

This permits nonzero negative proper fractions such as `-0.25`, while continuing to reject negative zero, leading plus/zeros, exponent notation and trailing insignificant zeros. All runtime Decimal zero values serialize as `0`. Integer tags and all existing F/X/W fixtures are unchanged. Additional cases under P4-T25/T57 are in `tests/p4/fixtures/decimal_fraction_cases.json`.

No new type/operation, P0/P1/P2/P3 change, dependency, P5 feature or Gate B closure.
