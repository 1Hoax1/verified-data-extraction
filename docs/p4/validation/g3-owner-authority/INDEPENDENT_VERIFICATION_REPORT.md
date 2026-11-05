# G3 owner-authority receipt — independent technical verification

**Result: PASS. Receipt status: PREPARED FOR MAIN MANAGING CHAT REVIEW / NOT PUBLISHED.** Verification timestamp (Europe/Moscow): 2026-11-05T14:41:13.293467+03:00.

This report recomputes the expected identities from freshly retrieved immutable GitHub objects and a separate fresh bare Git object database. It does not reuse an earlier receipt as technical proof. It is performed in the same Codex environment: this is an independent data/method check, not a new independent human approval, second-host execution or application regression.

## Verified values

| Field | Verified value |
|---|---|
| G3 | `d941714bc1d152d0a2189aa954e623460b4e6d03` |
| B3 | `be002c5b196b3a374c39fe511d2e1c68477723ab` |
| H3 | `c76e162cca8e044dcc78d3f52a52b57fd230592b17249b6048f6f753618b6d18` |
| L3 | 40572 bytes |
| M | `100644` |
| G3 tree | `c2200a045500928311bad5ec90619fcd5db5e3e0` |
| Direct parent | `edc40399a4a5db448278edd098bff4307b308dbd` |
| Previous G2 authority | `27cdea7b204c36e839f1c3b1a8de387f64c0a91e` |

All values match the task's expected values. The source branch `governance/p4-final-merge-reconciliation` resolved to G3 before and after collection. The observed main ref remained `edc40399a4a5db448278edd098bff4307b308dbd`. These refs are observations, not moving sources of authority: the receipt is bound only to the immutable G3 object.

## Exact identity and ancestry evidence

GitHub REST responses are retained under `evidence/api/`; actual GET commands are in `evidence/API_COLLECTION_COMMANDS.json`. A fresh full `git fetch` into an isolated bare repository supplied canonical object payloads. Commands/stdout/stderr are retained; no existing project worktree/config was used as the object source or changed by the fetch.

The canonical Git headers and payloads for 9 commit/tree/blob objects were independently rehashed with Git SHA-1 framing, including G3, G2 and the complete short first-parent path. Their raw bytes and hash/size inventory are under `evidence/git/` and `evidence/GIT_OBJECT_IDENTITIES.json`. Git SHA-1 identities agree with both GitHub REST and the freshly fetched object database. The API-decoded exact B3 bytes match the fetched Git blob. H3 was recomputed by both Python hashlib and `sha256sum`, without Unicode, decoding or newline transformations. Git mode is independently confirmed in both GitHub root-tree data and the fetched tree.

The verified first-parent lineage is:

`27cdea7b204c36e839f1c3b1a8de387f64c0a91e` → `2595ad45c962ad6ec5790261ecdaf59907ff8b40` → `edc40399a4a5db448278edd098bff4307b308dbd` → `d941714bc1d152d0a2189aa954e623460b4e6d03`.

GitHub compare reports G2 as the merge base, status `ahead`, ahead_by 16, behind_by 0; fresh Git `merge-base --is-ancestor` also passes. Parent→G3 compare reports exactly one commit. Merge-parent arrays are cross-checked against canonical commit headers; ancestry is preserved, not inferred from commit titles.

## Exact approved text and bounded change

The source is the owner-supplied reconciliation record from Main Managing Chat — Part 2, preserved as `evidence/APPROVED_RECONCILIATION_SOURCE.md`: 3616 bytes, SHA-256 `e07d23cd122202e2fec7d3032e2296804772c1d60a8d6f11ff56f9734a7eb607`. The G3 document is **exactly the entire 36955-byte parent document + one separator newline + that exact approved record**. The parent's document is also exactly the G2-authorized document. No historical byte was rewritten. API and Git agree: `DECISIONS.md` only, +80/−0 lines.

The historical `Decision status: PROPOSED — pending explicit owner approval` is intentionally untouched. The owner later explicitly confirmed **«Утверждаю запись P4 Final Merge Reconciliation в предложенной редакции»** on 2026-11-02, as supplied in this conversation. The receipt records that already-existing APPROVED decision; it does not replace source wording or invent a new approval. Neither G3 nor H3 is written into DECISIONS.

## No unauthorized changes

Complete non-truncated parent/G3 root-tree inventories have the same paths. Every entry except DECISIONS has identical mode/type/Git SHA. Equal subtree hashes preserve all production, tests, fixtures, contracts, migrations, dependencies, approved packages and historical validation evidence recursively. The detailed comparison is in `TECHNICAL_VERIFICATION.json`; fresh Git's full-tree diff also confirms the singleton path.

This change-scope assertion is **G3 versus its direct parent**. The broader G2→G3 ancestry includes the previously performed P4 integration; those earlier authorized changes are not falsely attributed to the G3 reconciliation commit.

Existing project worktree HEAD/status and DECISIONS/active-pin/verifier/P4-policy hashes match the pre-task snapshot. No code/test/pin/policy/DECISIONS mutation, commit, push, PR merge or P5 action was performed. The only Git writes were fetching existing remote objects into the separate verification database. Raw GitHub reads were GET operations only.

## Authority distinction and limitations

GitHub objects establish document identity, content and history; they do not authenticate a private human approval message. Owner authority is the explicit instruction supplied by the user, separately recorded in the receipt. The prior authorization to publish G3 covered that exact isolated-branch commit; it does not authorize publishing this receipt, modifying main, performing repin or starting P5.

The active pin still points to G2 and does not cover the G3 document. This task prepares the authority data needed by the binding CR-P4-005 follow-up; no repin is claimed complete. No pytest or new 212-test regression was run. The original reconciliation's historical acceptance statements remain historical, not new runtime evidence.

## Review handoff

Prepared JSON: `docs/p4/validation/P4_FINAL_MERGE_RECONCILIATION_G3_OWNER_AUTHORITY_RECEIPT.json`. Exact proposed evidence paths are listed in `PROPOSED_PUBLICATION_FILES.txt`; publication steps are in `PUBLICATION_PROCEDURE.md`. The SHA-256 manifest covers the JSON receipt and all package files except the manifest itself, using paths relative to the proposed repository root. No file contains its own checksum or its own future publication commit SHA.

**Return this package to Main Managing Chat — Part 2. Stop before publication, owner-authority receipt commit, governance repin, main merge or P5.**
