# Reproducing the admission finding

Use the exact source archive in `docs/p5/handoff/`; verify its SHA-256 and all nested manifests first. Original source documents stay byte-identical. Install only the existing pinned project/test dependencies in an isolated environment.

Create a detached worktree from the repository's actual Git object:

```bash
git worktree add --detach /tmp/vde-p5-historical fd39aa1bed480313504ae8b1f76e77e170cb72ba
```

Run the historical suite from that worktree with `src` and `tests` from that same tree on PYTHONPATH:

```bash
python -m pytest tests/p1 tests/p2 tests/p3 tests/p4 -q --junitxml=/tmp/vde-p5-historical.xml
```

The original tests emit some validation files in their checkout. Use a disposable worktree or the included historical recorder to capture their new outputs and preserve original tracked evidence bytes. `historical_recorder.py` is the exact external runner used here, with actual absolute paths; adjust only its worktree/output paths for another environment and retain that command/source variant with the new evidence. It is not an altered historical test.

For the numeric finding, run the included **read-only test probe** against that frozen worktree (the probe script itself can be outside it):

```bash
PYTHONPATH=/tmp/vde-p5-historical/src:/tmp/vde-p5-historical/tests \
python /path/to/reproduce_numeric_handoff.py \
  --repo /tmp/vde-p5-historical \
  --out /tmp/vde-p5-numeric-finding
```

Expected observation before any CR approval: **exit 1**, two failing compatibility JUnit cases, one P-A and four P-B integer-in-decimal cells. This is a reproduced blocker, not a successful P5 acceptance test. The script calls existing real P1/P3/P4 runtime through the unchanged P4 test helper in disposable fixture workspaces. It does not use a candidate P5 exporter, synthetic source schemas or new production Approval.

The four unchanged design/supplement verifier invocations and available-P0 validator invocation are preserved as exact argument arrays under their respective `command.json`; unpack source ZIPs to matching roots or record a new absolute-path variant. All actual stdout/stderr and exit codes are included. Do not treat their static golden reconstruction as a replacement for actual P4 handoff compatibility.

From repository root, verify review-package hashes with:

```bash
sha256sum -c docs/p5/validation/implementation-admission-20261106/MANIFEST.sha256
```

No CR-P5-003 semantic change is implemented by any reproduction step.
