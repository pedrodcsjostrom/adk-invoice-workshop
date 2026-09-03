# Run of show — 60 minutes

**Status: settled shape, timings from #22's measured run, unrehearsed as a whole.** Ticket [#11](https://github.com/pedrodcsjostrom/invoice_analysis/issues/11). [#15](https://github.com/pedrodcsjostrom/invoice_analysis/issues/15) is what turns the budgets into measurements.

## The one thing

> **Every attendee leaves having typed the re-read steps into the agent instruction and watched their own agent call the arithmetic check twice on the rigged invoice.**

Locally counts. Deploying does not count. If the room is on fire at 0:30, this is the thing that survives; everything after it is a bonus segment with a cut line already drawn.

## Shape of the hour

Two decisions carry the whole plan.

**Local first, cloud second.** The store falls back to a JSON Lines file when `FIRESTORE_DATABASE` is unset ([#9](https://github.com/pedrodcsjostrom/invoice_analysis/issues/9)), so nothing before 0:39 needs a working GCP project. The payoff moment is therefore out of reach of every cloud failure mode.

**The cloud work starts early and is collected late.** The deploy is not one block at the end. It splits in three: the first Terraform apply at 0:14, the container build submitted asynchronously at 0:30, and the collection at 0:39.

The machine time is small and now known. [#22](https://github.com/pedrodcsjostrom/invoice_analysis/issues/22) measured the whole path on a project created empty for the purpose:

| Step | Measured |
| --- | --- |
| First apply, hello container | 38s |
| `gcloud builds submit`, cold cache | 52s |
| Second apply, image swap | 29s |
| Container start to serving | 11s |
| Rigged invoice on Cloud Run | 18s |

So the split is not rescuing a plan from a five-minute build — it buys about ninety seconds out of the tail, and that is the smaller half of the reason. **The larger half is that 0:14 becomes a diversion point.** The apply depends on nothing the attendee types, so an attendee whose project is broken finds out with twenty minutes of runway to reach the sandbox. The same failure discovered at 0:39 has none. That argument holds whatever the build costs.

This also inverts the objection the draft was rejected on. An early cloud step does put a cloud failure before the payoff — and because the payoff is entirely local, that failure is *detected* early and *costs* nothing.

Hands-on time: roughly 35 of the 60 minutes.

---

## 0:00 — 0:05 · Open, and the promise (5 min)

One slide. The promise stated plainly: *by the end of the hour you will have deployed an agent that reads a real PDF invoice, catches one that does not add up, and files it anyway with a flag.*

Then 60 seconds of the finished thing on Peter's already-deployed service: upload, tool trace, records page with one red flagged row. They see the destination before they build it.

Say out loud, once, the thing that makes the hour make sense: **the failure is designed, and it is the point.** Otherwise the best minute of the hour reads as a bug.

**Cold-arrival triage happens here, in the first 60 seconds.** Hands up for anyone whose pre-flight did not pass. They get the sandbox handout ([#13](https://github.com/pedrodcsjostrom/invoice_analysis/issues/13)) — project id and service name, no credentials — and start their clone now. They run one segment behind until the first `solutions/` copy pulls them level. That is what the escape hatch is for.

> [!WARNING]
> **That last sentence does not survive [#13](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/13).** The sandbox is only the deployed service: `allAuthenticatedUsers` is refused on a project-level IAM policy, so a cold arrival cannot be granted Vertex on it and cannot run an agent of their own at all. They watch the payoff rather than producing it, which is the one thing this outline says every attendee must leave having done. A fallback attendee who "runs one segment behind" does not exist as built. [#37](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/37) decides what they actually do, and this paragraph is rewritten when it lands.

## 0:05 — 0:09 · The repo, and one command (4 min)

Tour the shape, not the code. `invoice_agent/` with agent, tools, validation, store and server; `samples/invoices/`; `data/vendor_registry.json`; `solutions/`; `infra/`.

Name the two gaps now so nobody is surprised by them. There are **two** escape
hatches, one per gap, and each already sits in the comment fence in the
attendee's own file. Say both out loud and write both on the whiteboard, where
they survive every screen switch:

```
cp solutions/tools.py invoice_agent/tools.py     # fill-in one, needed from 0:09
cp solutions/agent.py invoice_agent/agent.py     # fill-in two, needed from 0:25
```

Everyone runs one command:

```
uv run pytest tests/test_gap_arithmetic.py
```

It goes **red**, and that is correct. Five seconds, no cloud calls. It proves their environment works and it defines the next five minutes in the same breath.

## 0:09 — 0:14 · Fill-in one: the arithmetic tool (5 min)

Type `check_invoice_arithmetic` in `invoice_agent/tools.py`: signature, docstring, one-line delegation to `validation.check`. About 15 lines.

The teaching line, which is the whole reason this block is typed rather than shipped: **the docstring is prompt text.** It is not documentation for a human reading the file later, it is the only thing telling the model when to reach for this tool and what to put in it. Write it badly and the agent never calls it.

Verify: the same pytest, now green, in five seconds.

## 0:14 — 0:18 · Cloud step one, over the top of the backstop (4 min)

Two things at once, and the ordering matters: the command goes first, the talking happens over it.

```
cd infra && terraform apply -auto-approve
```

Thirty-eight seconds, nine resources ([#8](https://github.com/pedrodcsjostrom/invoice_analysis/issues/8), timed in [#22](https://github.com/pedrodcsjostrom/invoice_analysis/issues/22)). The `image` variable defaults to Google's public hello container, which is exactly what lets this run before any image exists — and is why this step can move here at all. It has **no dependency on anything the attendee types**, which no other cloud step can claim.

`terraform init` is not run here. The pre-flight already ran it, so the provider is on disk rather than coming down over conference wifi forty times at once.

While it runs: anyone still red on the gap test copies the solution file, and the loop gets explained with the instruction on screen. An agent is a model, a set of tools, and an instruction, run in a loop until it stops asking for tools. Show `INSTRUCTION` as it currently ships — steps 1, 2 and 5-8 present, steps 3 and 4 fenced and empty. As it stands the agent extracts, checks the arithmetic once, and saves.

**This is the diversion point.** Anyone whose apply fails goes to the sandbox now, with twenty minutes of runway and nothing important missed. Do not debug an individual project from the front of the room.

## 0:18 — 0:25 · First run, local (7 min)

```
adk web
```

Warn the room before they run it, because forty laptops hit this simultaneously: **a telemetry consent dialog and two alarming-but-harmless warnings** ([#4](https://github.com/pedrodcsjostrom/invoice_analysis/issues/4)). If the pre-flight makes them run `adk web` once the day before, this cost disappears — see the consequences below.

Upload a clean invoice first. Eleven to twenty seconds. Read the tool trace together as a group: extraction, one call to `check_invoice_arithmetic`, `lookup_supplier`, `save_invoice_record`.

Then upload `04-halden-rigged-total.pdf`. It fails the check once and saves the record flagged. Correct behaviour, and completely invisible — **it never went back to the document.** Point at exactly that absence. It is the setup for the next five minutes, and it is why fill-in two lands here and not at the start ([#10](https://github.com/pedrodcsjostrom/invoice_analysis/issues/10)).

Seven minutes because this is where first-launch friction lives: the port, the dialog, the warnings, the first upload.

## 0:25 — 0:30 · Fill-in two: the re-read (5 min)

Type steps 3 and 4 of `INSTRUCTION` in `invoice_agent/agent.py`. Twelve lines of English: re-read the document when the check fails, then **call the check again even if nothing changed.**

The teaching line: you are not writing code here, you are writing policy. And the clause that feels redundant — check again when the reading did not change — is the entire reason anyone will be able to see the agent think. No test on this block, by decision. The run that proves it is the payoff.

Prose is also the right thing to be typing under clock pressure. A typo is harmless.

## 0:30 — 0:31 · Cloud step two: submit the build (1 min)

One command, in the second terminal, and then it is forgotten about:

```
gcloud builds submit --async
```

Fifty-two seconds on a cold cache, so it is finished well before anyone looks at it again. `--async` is still the right flag: without it the command streams build logs and holds the terminal through the best segment of the hour, for no benefit.

**Why the build lands exactly here** and not at 0:14 with the apply: the image is built from the agent source, so a build submitted before this moment ships an agent with an unimplemented arithmetic tool and no re-read steps. It would deploy cleanly and then fail in front of everyone at 0:41. This is the earliest minute at which the source is the finished source, and that constraint — not the clock — is what pins it here.

The cost of `--async` is that a failed build is silent until 0:39. Accepted: the collection step surfaces it, the payoff has already happened, and a synchronous rebuild costs the deploy segment and nothing else.

## 0:31 — 0:36 · The payoff (5 min)

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

## 0:36 — 0:39 · Slack (3 min)

Questions, catch-up, breath. This block exists to be spent.

## 0:39 — 0:44 · Collect the deploy (5 min)

- **0:39** Check the build landed, with `gcloud builds describe <id>` or the tail of `gcloud builds list`. A failure surfaces here and the answer is a synchronous rebuild while the room moves on without them.
- **0:40** Second `terraform apply`. Twenty-nine seconds, one revision replaced, then eleven more before the container is serving.
- **0:41** `gcloud run services proxy` in a spare terminal, browse localhost. This terminal stays running for the rest of the hour. There is no public URL anywhere in the kit and no branch in the instructions ([#18](https://github.com/pedrodcsjostrom/invoice_analysis/issues/18)).
- **0:42** Upload the rigged invoice once more. Eighteen seconds, and **the same double check appears** — #22 confirmed the demo survives the deploy, running as the stack's service account rather than as a human. Now it writes to Firestore and archives the PDF to Cloud Storage.
- **0:43** Open the records page on the same service. One deployable, and now they have seen why that claim is true rather than aspirational.

Talk over the waits: why `min_instance_count = 0` is the 86x lever on idle cost, and why the service runs as its own service account rather than the Compute Engine default.

## 0:44 — 0:49 · Teardown, live, together (5 min)

```
scripts/teardown.sh
```

Nobody leaves the room with something running. It has now been run against a live stack ([#22](https://github.com/pedrodcsjostrom/invoice_analysis/issues/22)), sweeping the Cloud Build staging bucket and shutting the project down.

Then the split from `docs/COST.md`: on the $300 free trial a surprise bill is structurally impossible, because Google closes a trial account rather than upgrading it. Attendees on an existing paid billing account are the ones who need the $5 budget alert, and they are the only ones addressed by that page.

This segment is not cuttable. It is compressible to sixty seconds of "run this now, I will wait."

## 0:49 — 0:57 · What that was, and where it goes (8 min)

Three points, no slides needed:

1. A tool's description is its interface. English is the type signature.
2. The interesting behaviour is in the loop, not the model. Nothing clever happened in any single call.
3. An agent you cannot watch is an agent you cannot trust. The trace was the product.

Then the take-home: what to change first, and what this toy is missing before it is real.

## 0:57 — 1:00 · Questions and the URL (3 min)

Repo URL on screen and recitable. Feedback ask.

---

## Cut list, in order

The room will run late. Cut in this order and say nothing about it:

1. **Slack at 0:36** (3 min). It exists to be spent.
2. **The cloud run of the rigged invoice at 0:42** (2 min). Prove the service answers and move on; they already did the real thing locally.
3. **The wrap-up at 0:49** compresses from 8 minutes to 3. The take-home is in the README.
4. **Their own records page at 0:43** (1 min). Show Peter's instead.
5. **The clean-invoice run at 0:18** (2 min). Go straight to the rigged one. Costs the contrast, which is a real loss.

**Never cut:** fill-in two, the payoff run, and teardown. If the collection will not fit before 0:44, the collection is what gets abandoned — not the centerpiece and not the teardown. An attendee who leaves with a built image and no deployed revision has a two-command take-home, which is a decent consolation prize and worth saying out loud.

## Still open

1. **The proxy path is unproven.** This is now the largest hole. #22 reached the deployed service on its `run.app` URL with an identity token — which proves the service, but **not the route every attendee takes at 0:41**. The `cloud-run-proxy` component is genuinely absent from an apt-installed gcloud and will not install without sudo, exactly as #8 predicted. The pre-flight check on #12 is the only thing standing between an attendee and a service they cannot open, and #15 must rehearse *through* the proxy rather than around it.
2. **Three terminals** by 0:41: the developer UI, gcloud and Terraform, and the proxy. Nobody has been asked to manage that yet, and the pre-flight is the place to warn them.
3. **`terraform apply -auto-approve`** assumes the room should not be typing `yes` while listening to an explanation. Fine for a workshop, and worth one sentence about why it is not what you would do at work.
4. **Whether `adk web` needs a restart** to pick up an edited `INSTRUCTION`. The payoff segment assumes it does. If ADK reloads it, the segment gets smoother and a minute cheaper.
5. **The measured numbers came from one machine on good wifi**, in `europe-west1`. Conference wifi is the variable none of them account for, and the build's 52 seconds includes a source upload.

## Consequences for other tickets

- **[#12 pre-flight](https://github.com/pedrodcsjostrom/invoice_analysis/issues/12)** — four additions. Run `terraform init` so the provider is on disk, now load-bearing rather than a nicety, because the apply at 0:14 has no room for a download. Run `adk web` once and dismiss the telemetry consent dialog, so the room does not hit it forty times at once. Run the gap test so the red result is familiar. And warn about three terminals. The `cloud-run-proxy` check inherited from #8 is the single most important item on the list.
- **[#15 rehearsal](https://github.com/pedrodcsjostrom/invoice_analysis/issues/15)** — rehearse against this file, through the proxy, on the worst wifi available. The two things to test under pressure are the cut list and whether an attendee can actually open the service at 0:41.
- **[#32 speaker materials](https://github.com/pedrodcsjostrom/invoice_analysis/issues/32)** — four windows need prepared narration rather than improvisation: the apply at 0:14, the rigged run at 0:31, the build check at 0:39 and the second apply at 0:40.
