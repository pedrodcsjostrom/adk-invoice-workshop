# Rehearsal: the full hour, run against a clean clone and a fresh project

Ticket [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15).
Run on 2026-09-03, Linux, `gcloud` 583.0.0 from apt, Terraform 1.13.5, Python
3.12.3, `uv` 0.9.26.

**This is a partial rehearsal.** The local half ran end to end and is measured
below. The cloud half did not run: `terraform apply` was refused by the sandbox
this session ran under, and `cloud-run-proxy` cannot be installed without a
password. What is still owed is listed at the bottom, and #15 stays open until
it is done.

## What the rehearsal found before it ran anything

`main` had no agent gaps in it. The attendee-facing layer built by
[#25](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/25) —
`solutions/`, both fenced fill-ins, `tests/test_gap_arithmetic.py`,
`tests/test_solutions_in_step.py`, `scripts/cut_workshop_tag.sh` — was merged
into a branch that had already been merged, so it existed nowhere on the default
branch. The pinned tag could not be cut, which is the rehearsal's first step and
the attendee's first command.

Landing it exposed two more:

- `solutions/agent.py` had drifted outside the fence, because `main` had since
  moved the model to `INVOICE_MODEL`. Copying the solution over would have
  reverted that. The drift guard caught it, which is the first time that test
  has earned its keep.
- `scripts/cut_workshop_tag.sh` printed the pre-rename clone URL and a
  `cd invoice_analysis` that no longer exists. That text is read out from the
  front of the room.

## The defect that matters: the before state was not reliably "before"

The hour turns on a before-and-after. At 0:22 the room runs the rigged invoice
and points at the **absence** of a re-read; at 0:31, having typed fill-in two,
they watch the same invoice get checked twice.

Measured on a fresh clone with fill-in two empty, the agent checked twice
anyway in **3 of 12 runs**. Around a quarter of the room would have seen the
payoff before typing anything, and then seen nothing change when they did.

The cause is that step 5 sits **outside** the fill-in fence, so it is in the
prompt even when the re-read block is empty, and it said:

> If **the second check** also reports ok=false ... Do not check **a third
> time**.

Two phrases asserting a second check exists. The model sometimes obliged.

Step 5 now refers to what the steps above actually ask for rather than
presupposing a count. Measured after the change:

| State | Instruction | Trials | Checked twice |
| --- | --- | --- | --- |
| Before, fill-in two empty | original | 12 | 3 |
| Before, fill-in two empty | reworded | 16 | 0 |
| After, fill-in two typed | reworded | 8 | 8 (all exactly two) |

The after state was never in doubt — it was 8 of 8 on the original wording too,
matching [#7](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/7).
The fix is one-sided: it removes the leak without touching the payoff.

The general lesson, and it is worth saying in the room at 0:25: **a fill-in
gap is only empty if the prose around it does not describe what is missing.**
Prompt text has no scope.

## Timings

| Step | Measured | Run of show says |
| --- | --- | --- |
| Enable the eight APIs | 85s | "a few minutes to propagate" |
| `git clone` | 2s | — |
| `terraform -chdir=infra init` | 4.8s | pre-flight, off the clock |
| `scripts/preflight_check.sh` | ~40s | — |
| Clean invoice, local | 20.0s | 11-20s |
| Rigged invoice, before state | 18.8-19.4s | — |
| Rigged invoice, after state | 27-34s (#7) | 27-34s |

The clean local run landed at the **top** of its stated 11-20 second budget, not
the middle. The 0:18-0:25 block has seven minutes for two uploads and first-launch
friction, so this is not yet a problem, but the budget should not be trimmed.

## The pre-flight script, run for real

Thirty checks, and it correctly reported `NOT READY — 1 thing(s) to fix` on the
one genuine gap. Everything else passed on a project created minutes earlier,
including the check that matters most:

- **`gemini-3.5-flash` answered at `global`** on a project whose APIs had been
  enabled 0 minutes before. The script warned about propagation, as designed,
  and the model call worked anyway. The ten-minute wait in
  [#3](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/3) is
  sound advice to keep, but it is a margin rather than a hard floor.
- The `cloud-run-proxy` check failed and printed the exact `apt-get` line.
  `apt-cache policy` confirms `google-cloud-cli-cloud-run-proxy` is available at
  `583.0.0-0`, an exact version match for the installed gcloud, which settles
  [#12](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/12)'s
  finding against
  [#8](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/8)'s and
  [#22](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/22)'s
  belief that it was uninstallable. It does need a password, which is why it
  belongs in the pre-flight and not in the hour.

One check looked wrong and is not. "The developer UI has been opened on this
machine" passed on a clone where `adk web` had never run, because the check also
accepts `$HOME/.adk`. That directory holds `config.json` with the telemetry
answer, which is per-machine and survives a re-clone. Since the consent dialog
is the thing that costs the room time, the pass is correct. Worth knowing before
someone "fixes" it.

## Still owed, and #15 is not done without it

1. **The cloud half.** `terraform apply`, `gcloud builds submit --async`, the
   second apply with `-var "image=$IMAGE"`, and the records page. #22 measured
   this path (38s, 52s, 29s) on its own project; it has not been run on this
   clone with the landed gaps.
2. **The proxy at 0:41.** Still the largest hole in the kit. #22 went round it
   with an identity token, #13 could not install the component, and this run
   could not either. Nobody has yet opened the deployed agent the way every
   attendee is told to. If a password is not available, the pre-flight's own
   escape route applies: install the tarball SDK into a home directory, which
   takes components without root.
3. **`scripts/teardown.sh` against a live stack.** Written and reasoned in
   [#14](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/14),
   never run against real resources.
4. **The tag.** `scripts/cut_workshop_tag.sh` had all three of its gates pass on
   a clean clone of `main`, but the tag itself was not pushed from this session.
   Cut it before the pre-flight email goes out.
5. **The cut list under pressure**, and the hour run against a wall clock with a
   real room rather than block by block.
