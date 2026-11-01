# Stage B evidence publication

This evidence-only publication copies all 122 files from the completed Stage B evidence archive byte-for-byte. It adds publication metadata, a complete added-file inventory and a publication checksum manifest. It does not rerun tests, reconstruct logs, modify original evidence or change implementation/approval status.

**Tested commit:** `a868134fb9f3118bd5e56c26662db55fe281430d`.  
**Tested tree:** `0150b2eccb498d86b6e0ecf2cbc854a6de381f39`.

The publication commit is a direct descendant of that tested commit and only adds this directory. Its new tree includes evidence; the original 212/212 PASS result belongs to the exact tested tree above. It is not a claim of a new pytest run on the publication commit.

`STAGE_B_VALIDATION_REPORT.md` and `POST_PUBLISH_VERIFICATION.json` are preserved original records. Their wording about external packaging, the prior integration HEAD and nine implementation changes describes the completed Stage B run before this later publication. `CHANGED_FILES.txt` likewise lists the nine CR-P4-005 implementation files. The full list added by **this publication** is `PUBLICATION_ADDED_FILES.txt`.

## Saved results

- `runs/positive-02/`: exact P2-T40/P3-T51 command, stdout/stderr, exit code, environment and JUnit (2 PASS).
- `runs/scope-02/`: P4-T61/T62/T63 evidence (3 PASS), including nested regression and governance probes.
- `runs/full-01/`: full 212-ID regression (P1 42, P2 54, P3 52, P4 64), zero failures/errors/skips/xfails.
- `runs/full-01/generated/docs/p4/validation/cr-p4-005/governance-results.json`: P01-P05 and N01-N14, 19 criteria/59 subcases and Git-driver logs.
- `runs/full-01/generated/docs/p4/validation/stress.*`: original load command/output, measured resource results and exit code.
- `runs/full-01/generated/`: F38/X19/W45, real P0/goldens/strict verifier, crash/restart logs and nested regression evidence.
- `runs/independent-n09/`: separate saved receipt-comparison check on the same tested code/tree. P05 remains a scoped test-only authority simulation; N09 retains the human approval/review trust boundary explained in the original report.
- `development-attempts/`: earlier attempts are retained as history, including the corrected Unicode probe failure; they are not final passing-run evidence.

## Checksums and preservation

`MANIFEST.sha256` is the untouched original manifest: 121 hashes covering the original payload except that manifest itself. `PUBLICATION_MANIFEST.sha256` covers all published files, including the original manifest and the three other new publication metadata files, except its own checksum file. No manifest contains its own hash. `PUBLICATION_VERIFICATION.json` records source/archive identity and checks made against the existing saved logs, JUnit and tested Git objects.

From this directory, both checks must pass:

```bash
sha256sum -c MANIFEST.sha256
sha256sum -c PUBLICATION_MANIFEST.sha256
```

The source archive SHA-256 is `a077e48006d93107c603352086371e97f5784eaed2ec0f60f954f17b5f5cee7a` (239064 bytes). The archive itself is not duplicated in Git; its complete extracted contents are published here.

No production code, tests, DECISIONS, governance pin, dependencies, migrations, approved documents or prior validation files changed. Main and PR #4 are not merged or updated by this publication.

**Ready for final Gate B review. Gate B remains NOT_CLOSED; P4 remains IN_IMPLEMENTATION; PR #4 remains DRAFT / UNMERGED. Only the owner may approve Gate B or declare P4 VALIDATED.**
