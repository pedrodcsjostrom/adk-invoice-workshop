# Rehearsal: the full hour, run against a clean clone and a fresh project

Ticket [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15).
Run on 2026-09-03, Linux, `gcloud` 583.0.0 from apt, Terraform 1.13.5, Python
3.12.3, `uv` 0.9.26.

**The whole path ran**, from a clean clone against a project created empty for
it, through the proxy, ending with the project shut down. Everything below is
measured rather than budgeted. What is still owed — and it is not much — is at
the bottom.

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

| Step | Measured | Previously stated |
| --- | --- | --- |
| Enable the eight APIs | 85s | "a few minutes to propagate" |
| `git clone` | 2s | — |
| `terraform -chdir=infra init` | 4.8s | pre-flight, off the clock |
| `scripts/preflight_check.sh` | ~40s | — |
| Clean invoice, local | 20.0s | 11-20s |
| Rigged invoice, before state | 18.8-19.4s | — |
| Rigged invoice, after state | 27-34s (#7) | 27-34s |
| **First `terraform apply`, nine resources** | **58s** | **38s (#22)** |
| `gcloud builds submit --async` returns | 4-8s | — |
| Build, cold cache | 48s build phase, 59s submit to done | 52s (#22) |
| Build, warm cache | 37s build phase, 44s submit to done | — |
| **Second `terraform apply`, image swap** | **41s including container start** | 29s + 11s (#22) |
| Rigged invoice, **deployed, through the proxy** | 18.3s | 18s (#22, via token) |
| `scripts/teardown.sh` | 32s | — |

Two corrections and one confirmation. The **first apply is 58 seconds, not 38** —
twenty seconds over what #22 measured and what `DEPLOY.md` and the run of show
both still printed. The 0:14-0:18 block has four minutes, so it fits, but the
number was wrong. The second apply and the deployed run were both accurate.

The clean local run landed at the **top** of its stated 11-20 second budget, not
the middle. The 0:18-0:25 block has seven minutes for two uploads and first-launch
friction, so this is not yet a problem, but the budget should not be trimmed.

## The proxy at 0:41, finally proved

This was the largest hole on the map. #22 reached the service on its `run.app`
URL with an identity token, #13 could not install the component, and both
concluded it needed root. It does not.

The pre-flight's own escape route works, and it is quick: the tarball SDK
downloads in 6s (83 MB), extracts in 2s, and takes `cloud-run-proxy` in **9
seconds with no password at all**. Through the resulting proxy:

| Route | Result |
| --- | --- |
| `/` | 307 to the developer UI |
| `/dev-ui/` | 200 |
| `/records` | 200 |

So the deployed agent opens the way every attendee is told to open it, and
"one deployable" holds through the proxy rather than only on the `run.app` URL.

**One hazard the tarball route introduces**, and the pre-flight should say so:
gcloud warns that there are now two installations on `PATH`. An attendee who
installs the tarball but keeps calling the apt `gcloud` gets a proxy component
that is still missing, with no obvious reason why. The `sudo apt-get install`
line the check script already prints stays the better answer where a password
exists.

## The deployed run, and the store behind it

The rigged invoice through the proxy gave the trace the hour is sold on:

```
check_invoice_arithmetic -> check_invoice_arithmetic -> lookup_supplier -> save_invoice_record
```

Two checks with the re-read between them, in 18.3s, running as the stack's
service account rather than as a human. The record reached the **named**
Firestore database and the records page rendered it at 1 filed, Halden
Industrial Fasteners AS, 12,671.00 NOK, marked failing — and the original PDF
was in the bucket. #9's persistence and #22's deploy both hold together on one
service.

## Teardown, run against live resources for the first time

#14 wrote and reasoned `scripts/teardown.sh`; nothing had ever destroyed
anything with it. It works. Thirty-two seconds, nine resources destroyed, the
`_cloudbuild` staging bucket swept along with its two source tarballs, the
second regional bucket form correctly reported absent, and all five "what is
left" checks clean. `--delete-project` then shut the project down and printed
the `undelete` command.

The residue it reports on the laptop — `terraform.tfstate`, its backup, and
`invoice_agent/.env` — is correct and worth leaving alone. It warns rather than
deletes, which is right for a file an attendee may want.

## A mistake worth keeping

This rehearsal built the image before the source was final, and shipped a
container whose agent had an **empty re-read**. It deployed cleanly and would
have failed in front of the room at 0:42, checking once.

That is precisely the failure the run of show pins the build at 0:30 to avoid,
and the reasoning in that block is now confirmed by someone walking into it. If
the build ever moves earlier, this is what happens.

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

## Still owed

1. **The tag.** `scripts/cut_workshop_tag.sh` had all three of its gates pass on
   a clean clone of `main`, but the tag itself was not pushed from this session.
   Cut it before the pre-flight email goes out — it is one command and it is the
   attendee's first.
2. **The hour against a wall clock, with a room.** This was run block by block,
   not continuously, and by one person who already knew every answer. What that
   cannot test is the cut list under pressure, forty laptops on conference wifi,
   and how long forty people take to type twelve lines of prose.
3. **The cold-arrival path end to end.** #40 proved the group grant and measured
   the join at three seconds, but nobody has sat down as a cold arrival and done
   the local half against the sandbox.

Machine time for the whole cloud path, apply to serving agent: **about two and a
half minutes**, on good wifi, with the build async and off the clock.
