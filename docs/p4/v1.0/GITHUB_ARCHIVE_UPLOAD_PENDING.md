# P4 v1.0 APPROVED — GitHub binary upload pending

**Status:** PENDING (not uploaded by this commit; do not cite a nonexistent repository ZIP).  
**Owner:** main managing chat; approved design Gate A CLOSED / PASS on 2026-10-30.  
**Required action before separate P4 implementation start:** upload exact verified archive `P4_Implementation_Pack_v1.0_APPROVED.zip` to `docs/p4/v1.0/P4_Implementation_Pack_v1.0_APPROVED.zip`.

## Exact file identity

- **Approved ZIP SHA-256:** `e3c686f81e3ba0d63874420d0f67f7585b9861826fdbc8a76dfb6a5d8f2aa5aa`.
- **Size:** 112649 bytes. ZIP CRC PASS; internal manifest 53/53 PASS.
- Candidate preserved separately: `P4_Implementation_Pack_v0.4.1_candidate.zip` SHA-256 `79f725fd96075f3ca87b6172819d82b557f5e373b1f5ebc46f08cfbe8b2e3d0a`, 104894 bytes.
- The v1.0 ZIP adds approval/CR/decision/strict-validation/assembly evidence only; all original 48 candidate payload files retained byte-for-byte.
- **Do not recreate ZIP just from markdown:** arbitrary repacking changes SHA-256. Upload the exact approved binary supplied in the main chat.

## Procedure

1. Download the exact approved binary from the main chat.
2. In GitHub open `docs/p4/v1.0/` and choose Add file → Upload files (or use approved git/Codex upload workflow) to add the binary at the exact path.
3. Verify repository blob content has byte size 112649 and SHA-256 `e3c686f81e3ba0d63874420d0f67f7585b9861826fdbc8a76dfb6a5d8f2aa5aa`. Git blob SHA-1 is a different checksum and does not replace SHA-256.
4. After verifying the actual GitHub object, update this status record to VERIFIED and add its upload commit SHA to `DECISIONS.md`.
5. Request separate P4 implementation-start authorization; do not equate Gate A approval with code permission.

**Reason pending:** GitHub connector supports Git tree/commit mutation and UTF-8 text but does not accept this sandbox's local ZIP bytes for binary upload; container has no GitHub DNS/auth. Governance docs are uploaded now; no claim of a completed binary upload is made.
