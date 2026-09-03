# Run of show — 60 minutes

**Status: draft, for arguing with.** Ticket [#11](https://github.com/pedrodcsjostrom/invoice_analysis/issues/11). Timings are budgets, not measurements; [#15](https://github.com/pedrodcsjostrom/invoice_analysis/issues/15) is what turns them into measurements.

## The one thing

> **Every attendee leaves having typed the re-read steps into the agent instruction and watched their own agent call the arithmetic check twice on the rigged invoice.**

Locally counts. Deploying does not count. If the room is on fire at 0:30, this is the thing that survives; everything after it is a bonus segment with a cut line already drawn.

## Shape of the hour

The hour runs **local first, cloud second**. The store falls back to a JSON Lines file when `FIRESTORE_DATABASE` is unset ([#9](https://github.com/pedrodcsjostrom/invoice_analysis/issues/9)), so the first 33 minutes need no GCP project at all. That ordering is deliberate: the payoff moment is protected from every cloud failure mode, and the longest, most variable, most likely-to-break segment sits at the end where running long costs the least.

Hands-on time: roughly 34 of the 60 minutes.

---

## 0:00 — 0:04 · Open, and the promise (4 min)

One slide. The promise stated plainly: *by the end of the hour you will have deployed an agent that reads a real PDF invoice, catches one that does not add up, and files it anyway with a flag.*

Then 60 seconds of the finished thing on Peter's already-deployed service: upload, tool trace, records page with one red flagged row. They see the destination before they build it.

Say out loud, once, the thing that makes the hour make sense: **the failure is designed, and it is the point.** Otherwise the best minute of the hour reads as a bug.

**Cold-arrival triage happens here, in the first 60 seconds.** Hands up for anyone whose pre-flight did not pass. They get the sandbox handout ([#13](https://github.com/pedrodcsjostrom/invoice_analysis/issues/13)) — project id and service name, no credentials — and start their clone now. They run one segment behind until the first `solutions/` copy pulls them level. That is what the escape hatch is for.

## 0:04 — 0:08 · The repo, and one command (4 min)

Tour the shape, not the code. `invoice_agent/` with agent, tools, validation, store and server; `samples/invoices/`; `data/vendor_registry.json`; `solutions/`; `terraform/`.

Name the two gaps now so nobody is surprised by them. Say the escape hatch out loud and leave it on screen for the whole hour:

```
cp solutions/tools.py invoice_agent/tools.py
```

Everyone runs one command:

```
uv run pytest tests/test_gap_arithmetic.py
```

It goes **red**, and that is correct. Five seconds, no cloud calls. It proves their environment works and it defines the next five minutes in the same breath.

## 0:08 — 0:13 · Fill-in one: the arithmetic tool (5 min)

Type `check_invoice_arithmetic` in `invoice_agent/tools.py`: signature, docstring, one-line delegation to `validation.check`. About 15 lines.

The teaching line, which is the whole reason this block is typed rather than shipped: **the docstring is prompt text.** It is not documentation for a human reading the file later, it is the only thing telling the model when to reach for this tool and what to put in it. Write it badly and the agent never calls it.

Verify: the same pytest, now green, in five seconds.

## 0:13 — 0:16 · Backstop, and what a loop is (3 min)

Anyone still red copies the solution file. While they do, explain the loop out loud with the instruction on screen: an agent is a model, a set of tools, and an instruction, run in a loop until it stops asking for tools. Show `INSTRUCTION` as it currently ships — steps 1, 2 and 5-8 present, steps 3 and 4 fenced and empty. As it stands the agent extracts, checks the arithmetic once, and saves.

## 0:16 — 0:23 · First run, local (7 min)

```
adk web
```

Warn the room before they run it, because forty laptops hit this simultaneously: **a telemetry consent dialog and two alarming-but-harmless warnings** ([#4](https://github.com/pedrodcsjostrom/invoice_analysis/issues/4)). If the pre-flight makes them run `adk web` once the day before, this cost disappears — see the consequences below.

Upload a clean invoice first. Eleven to twenty seconds. Read the tool trace together as a group: extraction, one call to `check_invoice_arithmetic`, `lookup_supplier`, `save_invoice_record`.

Then upload `04-halden-rigged-total.pdf`. It fails the check once and saves the record flagged. Correct behaviour, and completely invisible — **it never went back to the document.** Point at exactly that absence. It is the setup for the next five minutes, and it is why fill-in two lands here and not at the start ([#10](https://github.com/pedrodcsjostrom/invoice_analysis/issues/10)).

Seven minutes because this is where first-launch friction lives: the port, the dialog, the warnings, the first upload.

## 0:23 — 0:28 · Fill-in two: the re-read (5 min)

Type steps 3 and 4 of `INSTRUCTION` in `invoice_agent/agent.py`. Twelve lines of English: re-read the document when the check fails, then **call the check again even if nothing changed.**

The teaching line: you are not writing code here, you are writing policy. And the clause that feels redundant — check again when the reading did not change — is the entire reason anyone will be able to see the agent think. No test on this block, by decision. The run that proves it is the payoff.

Prose is also the right thing to be typing under clock pressure. A typo is harmless.

## 0:28 — 0:33 · The payoff (5 min)

Restart `adk web`, upload `04-halden-rigged-total.pdf` again.

Twenty-seven to thirty-four seconds, roughly double a clean run ([#7](https://github.com/pedrodcsjostrom/invoice_analysis/issues/7)). **Budget thirty seconds of narration** to fill it, and the narration is: what the model is doing right now, and why the second identical check is a design decision rather than a wasted call.

Then read the trace together:

```
check_invoice_arithmetic  5 lines, total 12,671.00  ->  ok: false, short by 1,400.00
check_invoice_arithmetic  5 lines, total 12,671.00  ->  ok: false, short by 1,400.00
lookup_supplier           "Halden Industrial Fasteners AS"  ->  SUP-0004
save_invoice_record       ->  validation_passed: false
```

Two checks with the re-read between them, then it saves anyway with every number exactly as printed. The store recomputes the arithmetic itself rather than trusting the agent's claim about it. An accounts payable system that silently discards invoices it dislikes is the wrong lesson.

**This is the one thing.** Everyone confirms out loud that they have two checks in their trace before the room moves on.

## 0:33 — 0:35 · Slack (2 min)

Questions, catch-up, breath. This block exists to be spent. It is the first thing cut and it should usually be gone.

## 0:35 — 0:47 · Deploy (12 min)

The long, variable, risky block, deliberately last.

- **0:35** `terraform init && terraform apply` in `terraform/`. Nine resources, about 50 seconds ([#8](https://github.com/pedrodcsjostrom/invoice_analysis/issues/8)). The `image` variable defaults to Google's public hello container, which is what lets this run before any image exists.
- **0:37** `gcloud builds submit`. **Duration unknown — the single biggest hole in this plan** ([#22](https://github.com/pedrodcsjostrom/invoice_analysis/issues/22)). Talk over it: what is in the container, why `min_instance_count = 0` is the 86x lever on idle cost, and why the service runs as its own service account rather than the Compute Engine default.
- **0:42** Second `terraform apply`, this time with the built image. Fast.
- **0:44** `gcloud run services proxy` in a second terminal, browse localhost. This terminal stays running for the rest of the hour. There is no public URL anywhere in the kit and no branch in the instructions ([#18](https://github.com/pedrodcsjostrom/invoice_analysis/issues/18)).
- **0:45** Upload the rigged invoice once more. Same agent, now writing to Firestore and archiving the PDF to Cloud Storage.
- **0:46** Open the records page on the same service. One deployable, and now they have seen why that claim is true rather than aspirational.

## 0:47 — 0:52 · Teardown, live, together (5 min)

```
scripts/teardown.sh
```

Nobody leaves the room with something running. Then the split from `docs/COST.md`: on the $300 free trial a surprise bill is structurally impossible, because Google closes a trial account rather than upgrading it. Attendees on an existing paid billing account are the ones who need the $5 budget alert, and they are the only ones addressed by that page.

This segment is not cuttable. It is compressible to sixty seconds of "run this now, I will wait."

## 0:52 — 0:58 · What that was, and where it goes (6 min)

Three points, no slides needed:

1. A tool's description is its interface. English is the type signature.
2. The interesting behaviour is in the loop, not the model. Nothing clever happened in any single call.
3. An agent you cannot watch is an agent you cannot trust. The trace was the product.

Then the take-home: what to change first, and what this toy is missing before it is real.

## 0:58 — 1:00 · Questions and the URL (2 min)

Repo URL on screen and recitable. Feedback ask.

---

## Cut list, in order

The room will run late. Cut in this order and say nothing about it:

1. **Slack at 0:33** (2 min). It exists to be spent.
2. **The cloud run of the rigged invoice at 0:45** (2 min). Prove the service answers and move on; they already did the real thing locally.
3. **The wrap-up at 0:52** compresses from 6 minutes to 2. The take-home is in the README.
4. **Their own records page at 0:46** (1 min). Show Peter's instead.
5. **The clean-invoice run at 0:16** (2 min). Go straight to the rigged one. Costs the contrast, which is a real loss.

**Never cut:** fill-in two, the payoff run, and teardown. If deploy cannot fit before 0:47, deploy is what gets abandoned — not the centerpiece and not the teardown.

## What this draft is least sure about

1. **The build duration is a guess.** The whole 12-minute deploy block rests on `gcloud builds submit` taking about five minutes. If it is nine, the block does not fit and deploy becomes a guided demo with a take-home script. [#22](https://github.com/pedrodcsjostrom/invoice_analysis/issues/22) must return a number.
2. **The rejected alternative: start the build early.** Kick off apply-one and the build at 0:08 so it bakes during the fill-ins, then collect it at 0:40. It buys maybe five minutes. Rejected here because it splits the room's attention during the only typing blocks, and it puts a cloud failure *before* the payoff, which is exactly the ordering the rest of this plan exists to avoid. Worth arguing about.
3. **Whether `adk web` needs a restart** to pick up an edited `INSTRUCTION`. The payoff segment assumes it does. If ADK reloads it, the segment gets smoother and a minute cheaper.
4. **Four minutes of opening is tight** when it also carries cold-arrival triage.
5. **Two terminals and a browser** on every laptop from 0:44. Nobody has been asked to manage that yet.

## Consequences for other tickets

- **[#12 pre-flight](https://github.com/pedrodcsjostrom/invoice_analysis/issues/12)** — add three: run `adk web` once and dismiss the telemetry consent dialog, so the room does not hit it forty times at once; run `terraform init` so the provider plugin is cached rather than downloaded over conference wifi; run the gap test and confirm it fails cleanly, which is the same command the room opens with.
- **[#22 containerize](https://github.com/pedrodcsjostrom/invoice_analysis/issues/22)** — return the build wall clock as a number, and answer whether an edited instruction needs a process restart.
- **[#15 rehearsal](https://github.com/pedrodcsjostrom/invoice_analysis/issues/15)** — this file is the script to rehearse against, and the cut list is the thing to test under pressure.
