# Proposed paths and publication procedure — not executed

Status: **review package only**. Existing owner approval applies to the reconciliation and publication of G3. Publication of this prepared receipt/evidence is a later operation after Main Managing Chat — Part 2 review and an appropriate explicit instruction.

## Exact proposed paths

- JSON receipt: `docs/p4/validation/P4_FINAL_MERGE_RECONCILIATION_G3_OWNER_AUTHORITY_RECEIPT.json`.
- Verification report: `docs/p4/validation/g3-owner-authority/INDEPENDENT_VERIFICATION_REPORT.md`.
- Technical results: `docs/p4/validation/g3-owner-authority/TECHNICAL_VERIFICATION.json`.
- This procedure: `docs/p4/validation/g3-owner-authority/PUBLICATION_PROCEDURE.md`.
- Complete file inventory: `docs/p4/validation/g3-owner-authority/PROPOSED_PUBLICATION_FILES.txt`.
- SHA-256 manifest: `docs/p4/validation/g3-owner-authority/MANIFEST.sha256`.
- Exact raw evidence and collection/verification scripts: the individually enumerated paths under `docs/p4/validation/g3-owner-authority/evidence/` in the complete file inventory. The inventory is exact; this description is not a wildcard authorization.

The supplied review archive mirrors those repository paths under `docs/`. Its complete file inventory includes every proposed artifact. No change belongs to DECISIONS, tests, pin/policies, runtime, contracts, old evidence, dependencies or migrations.

## Later publication, only after review/authorization

1. Reconfirm the immutable source G3 `d941714bc1d152d0a2189aa954e623460b4e6d03` and its G2 ancestry. Do not amend, rebase, squash or recreate G3; do not substitute latest main or a newer DECISIONS version.
2. Create a **new isolated evidence-publication branch** `governance/p4-g3-owner-authority-receipt` from exact G3. Keep the existing source branch unchanged. The new branch name is proposed here; it has not been created.
3. Copy only the exact reviewed files from this package to their listed paths. From the repository root run `sha256sum -c docs/p4/validation/g3-owner-authority/MANIFEST.sha256`. Compare the staged file set with `PROPOSED_PUBLICATION_FILES.txt`; every path must be a new receipt/evidence artifact, with staged bytes matching the manifest. No source/governance document changes or pre-existing-file overwrites are allowed.
4. Create one separate **receipt/evidence-only commit R3**, direct child of G3. R3 adds the receipt and listed evidence only. Do not write R3's own SHA, the receipt's own hash, the manifest hash or any new authority value back into DECISIONS. The receipt and manifest contain no self-hashes; the manifest excludes itself.
5. Verify G3→R3 ancestry, unchanged G3/B3/H3/L3/M and an exact allowed-file diff. Independently verify committed Git blob bytes against the manifest and the owner's reviewed package.
6. If publication is authorized, push only that new isolated evidence branch. Verify R3 SHA/parent/paths and receipt bytes through GitHub API; verify main, the original G3 source branch and active G2 pin remain unchanged. Do not create or merge a PR automatically. Report R3 outside DECISIONS and outside the receipt; no self-reference is needed.
7. Return the published evidence identities to Main Managing Chat — Part 2. **Stop before governance repin.** A later separately instructed limited-repin task can consume the verified G3 tuple under approved CR-P4-005, update only the permitted active pin/references and perform the required regression. This receipt does not grant P5 authorization or merge permission.

No command in this proposed procedure has been executed as a publication operation during preparation. Current repository files and refs were not changed; a separate bare verification database was used solely to read remote objects.
