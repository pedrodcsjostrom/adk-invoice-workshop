# Host runbook

**Status: written from the settled kit, unrehearsed.** Ticket [#45](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/45).

What Peter does, in order, with the commands. Everything else in `docs/` is
attendee-facing or explains itself; this file does neither. It says why nothing
and links out for the words.

- **Why the hour has this shape** — [`run-of-show.md`](run-of-show.md)
- **What to say over the four waits** — [`speaker-notes.md`](speaker-notes.md)
- **What is on the projector** — [`deck.md`](deck.md)
- **Vocabulary** — [`../CONTEXT.md`](../CONTEXT.md)

Print this. Three pages, and the state sheet is the first of them.

---

## State sheet

The only part of this file that changes between deliveries. Fill it in as you
go; every later step reads from it. None of it is ever committed — the sandbox
id and the group address are live doors on a public repo.

```
DATE               ____________________
TAG                ____________________   cloned into ~/workshop-live
DELIVERY_PROJECT   ____________________   created the day before, torn down at 0:44
SANDBOX_PROJECT    adk-sandbox-_________  printed once by sandbox.sh, morning of
ACCESS_GROUP       ____________@googlegroups.com
IMAGE              ____________________   set at 0:30, must survive to 0:40
REGION             europe-west1

Cold arrivals expected   ____   (silent + NOT-READY-needs-admin, from the reports)
Handouts printed         ____

Ports    adk web 8000  ·  delivery proxy 8080  ·  sandbox proxy 8081
```

---

## Preconditions

All six green before day-before step one. Each is true or false, not a
judgement.

- [ ] **The attendee-facing repo is on `main`** — gap fences, `solutions/`,
      `tests/test_gap_arithmetic.py`. [#44](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/44).
      Today it is not: [#25](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/25)'s
      pull request merged into an already-merged branch and `main` ships the
      finished agent. **Nothing below works until this lands.**
- [ ] **The tag is cut** at the tip of `main`, and a bare clone of it goes red
      on `tests/test_gap_arithmetic.py`.
- [ ] **The rehearsal is done** — [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15).
      It owns the proxy route at 0:41 and whether `adk web` reloads an edited
      instruction.
- [ ] **The QR codes are in the deck** — the repo short link on slides 1 and 5,
      the access group join page on slide 2. These never change between
      deliveries, so they are a gate, not a morning task. A QR code nobody has
      scanned is on screen in the first ten seconds.
- [ ] **The deck is exported** to a file you can present from, not Markdown.
- [ ] **The pre-flight email went out three days ago** and the reminder is
      scheduled for the morning before.

**T-3.** The email and its reminder are written out in
[`preflight-email.md`](preflight-email.md). If you did not send it, stop
planning the hour you have: you are running the sandbox for the whole room,
and the second apply and the teardown come out of the plan.

---

## Day before

Ninety minutes, most of it waiting. It ends with two things standing: a live
clone with a red test, and an empty project with its APIs on.

### 1 · Read the reports

Sort every reply into the three piles in
[`preflight-email.md`](preflight-email.md). The `RESULT` line is the only line
you read first, and `model ... reachable=true` is the one that means it
genuinely works rather than looks configured.

Reply to the fix-it-yourself pile with the one command from **their own**
report. Do not diagnose further; the script already did.

Handle the needs-an-admin pile personally, today. Ask whether a personal Google
account is available. If not, tell them now that they are on the sandbox, so it
arrives as a plan rather than a surprise.

Then write two numbers on the state sheet: cold arrivals expected, which is the
silent replies plus the unresolved admin cases, and handouts printed, which is
that number plus five.

### 2 · The live clone

You cannot run the hour from your development checkout. It ships the finished
agent, so there is no red test and nothing to type, and any leftover
`.local_records.jsonl` or `.adk/session.db` is on the projector when you open
the records page.

```bash
git clone --branch <TAG> https://github.com/pedrodcsjostrom/adk-invoice-workshop.git ~/workshop-live
cd ~/workshop-live
uv sync
```

### 3 · The delivery project

A fresh project, torn down live at 0:44. It is created today and not tomorrow
because the eight APIs must be enabled by hand at least ten minutes ahead and
never by Terraform ([#3](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/3)).

```bash
gcloud projects create <DELIVERY_PROJECT> --name="ADK Workshop Delivery"
gcloud billing projects link <DELIVERY_PROJECT> --billing-account=<YOUR_BILLING>
gcloud services enable \
  run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  compute.googleapis.com firestore.googleapis.com aiplatform.googleapis.com \
  iam.googleapis.com cloudresourcemanager.googleapis.com \
  --project <DELIVERY_PROJECT>
```

Then point the clone at it. The `gcloud config set project` comes before the
login, or the quota project is missing:

```bash
cd ~/workshop-live
cp invoice_agent/.env.example invoice_agent/.env
# GOOGLE_CLOUD_PROJECT=<DELIVERY_PROJECT>
# GOOGLE_CLOUD_LOCATION=global

printf 'project_id = "%s"\n' <DELIVERY_PROJECT> > infra/terraform.tfvars

gcloud config set project <DELIVERY_PROJECT>
gcloud auth application-default login
gcloud auth application-default set-quota-project <DELIVERY_PROJECT>
```

### 4 · Verify, and leave it red

```bash
cd ~/workshop-live
./scripts/preflight_check.sh              # READY, on your own machine too
terraform -chdir=infra init               # the provider on disk, load-bearing at 0:14
uv run pytest tests/test_gap_arithmetic.py   # must be RED
uv run adk web .                          # dismiss the telemetry dialog once, then quit
```

**Leave the gap test red.** If you fill in the tool tonight to check it works,
you arrive tomorrow with a green test and no way to show the before. Verify
against `solutions/` on a scratch copy if you need the reassurance:

```bash
cp -r ~/workshop-live /tmp/scratch && cd /tmp/scratch
cp solutions/tools.py invoice_agent/tools.py
cp solutions/agent.py invoice_agent/agent.py
uv run pytest tests/test_gap_arithmetic.py && uv run python scripts/smoke.py
rm -rf /tmp/scratch
```

### 5 · The room

Projector adapter. Laptop charger. Phone hotspot tested, because conference
wifi is the variable none of the measured numbers account for. Handouts
printed, minus the two blanks that do not exist until tomorrow.

---

## Workshop day, before the room

Forty minutes, and the first step takes six of them on its own.

### 1 · Stand up the sandbox

```bash
cd ~/dev/adk-invoice-workshop        # your DEV checkout
scripts/sandbox.sh
```

**Not from `~/workshop-live`.** The script builds the image from the directory
it runs in, and the tag has the gaps in it. Run it from the live clone and you
deploy an agent whose arithmetic tool raises and whose instruction never
re-reads — to the one service a cold arrival cannot work around.

It prints the project id once. Put it on the state sheet now; it is generated
per run and recoverable only from `~/.adk-invoice-sandbox/project-id`.

### 2 · Fill the two blanks and re-export the deck

Slide 2 carries the sandbox project id and the access group address, by design,
and it is the slide a cold arrival stares at. Fill both in, re-export, and open
the exported file to confirm the underscores are gone.

### 3 · The sandbox proxy, and the opening demo

This is the service you show in the first 60 seconds. It is not a fourth
terminal — start it minimized, on its own port, and never type in it again.

```bash
gcloud run services proxy invoice-agent \
  --region europe-west1 --project <SANDBOX_PROJECT> --port 8081
```

Then, in the browser, **actually run the demo once**: upload
`04-halden-rigged-total.pdf` at `localhost:8081`, confirm the double check
appears, and open `localhost:8081/records` to confirm the flagged row is there.
That verification is the point of using the sandbox for the opening — you prove
the cold arrivals' service works at the moment its correctness starts mattering.

Leave both tabs open. Tab one is the upload, tab two is the records page.

### 4 · The three terminals

Open all three now. Terminal 3 sits empty for forty minutes on purpose, because
creating a window is what goes wrong while you are talking.

| # | Job | Starting directory | Live from |
|---|---|---|---|
| 1 | The agent, `adk web`, restarted once at 0:31 | `~/workshop-live` | 0:18 |
| 2 | gcloud and Terraform. **Holds `IMAGE`. Do not close it.** | `~/workshop-live` | 0:14 |
| 3 | The delivery proxy | `~/workshop-live` | 0:41 |

Terminal 2 stays at the repo root all hour and uses `terraform -chdir=infra`.
It does not `cd infra`, because `gcloud builds submit` at 0:30 uploads the
working directory and needs the root. Speaker notes W1 prints `cd infra &&`;
that is the one command in the kit to ignore.

### 5 · Last checks

```bash
cd ~/workshop-live
uv run pytest tests/test_gap_arithmetic.py   # still RED
git status                                    # clean
```

Editor open on `invoice_agent/tools.py` with the fence on screen. Deck on
slide 1. Whiteboard carries both recovery lines, where they survive every
screen switch:

```
cp solutions/tools.py invoice_agent/tools.py
cp solutions/agent.py invoice_agent/agent.py
```

---

## In the room

Thirteen blocks. Same five lines every time.

### 0:00 — 0:05 · Open, the promise, and cold triage

- **On screen** — slide 1, then browser tab one, then slide 2.
- **You type** — nothing. The demo is already loaded on `localhost:8081`.
- **Room does** — watches, then hands up for anyone whose pre-flight did not pass.
- **Say** — the promise, then *the failure is designed and it is the point*. Then the three sandbox instructions from slide 2, in order: join the group, two `.env` lines, login plus quota project.
- **If it goes wrong** — a join that does not take gets a per-email grant on the spot: `gcloud projects add-iam-policy-binding <SANDBOX_PROJECT> --member=user:<email> --role=roles/aiplatform.user`, and the same again with `roles/serviceusage.serviceUsageConsumer`. Effective the instant it returns.

### 0:05 — 0:09 · The repo, and one command

- **On screen** — the editor, fences visible. No slide.
- **You type** — nothing. The room types:
  ```
  uv run pytest tests/test_gap_arithmetic.py
  ```
- **Room does** — runs it, gets red, five seconds, no cloud calls.
- **Say** — the 0:05 narration in [`speaker-notes.md`](speaker-notes.md), said over the editor. Both `cp` lines out loud, both on the whiteboard.
- **If it goes wrong** — a red that is an *import error* rather than an assertion is a broken `uv sync`. Send them to the sandbox at 0:14 like anyone else.

### 0:09 — 0:14 · Fill-in one, the arithmetic tool

- **On screen** — the editor, `invoice_agent/tools.py`.
- **You type** — the tool, with them. Signature, docstring, one-line delegation to `validation.check`.
- **Room does** — types it, then the same pytest, now green in five seconds.
- **Say** — the docstring is prompt text. It is not documentation, it is the only description the model ever sees. Write it badly and the agent never calls this.
- **If it goes wrong** — still red at 0:14 means copy the solution file, which is the first thing you say over the apply.

### 0:14 — 0:18 · Cloud step one, and the diversion

- **On screen** — terminal 2, then slide 4, then the editor, then terminal 2.
- **You type** — command first, talking after. Do not narrate the typing.
  ```
  terraform -chdir=infra apply -auto-approve
  ```
- **Room does** — the same, on their own project. 38 seconds, nine resources.
- **Say** — narration **W1**. Then the diversion line, verbatim, once, to the whole room.
- **If it goes wrong** — an attendee's apply fails: slide 2, the same slide as 0:01, and they take the sandbox route. **Do not ask what the error was and do not debug from the front.** More than a quarter of the room failing is not a diversion; see Aborts.

### 0:18 — 0:25 · First run, local

- **On screen** — terminal 1, then the browser on `localhost:8000`.
- **You type**
  ```
  uv run adk web .
  ```
- **Room does** — the same, then uploads `01-northwind-clean.pdf`, then `04-halden-rigged-total.pdf`.
- **Say** — warn about the consent dialog and the two harmless warnings **before** they run it, because forty laptops hit it at once. Then read the clean trace together. Then, on the rigged one: it failed the check once, saved it flagged, and **never went back to the document**. Point at exactly that absence.
- **If it goes wrong** — a 403 on the first model call is a missing quota project, on a sandbox attendee or otherwise: `gcloud auth application-default set-quota-project <their project>`.

### 0:25 — 0:30 · Fill-in two, the re-read

- **On screen** — the editor, `invoice_agent/agent.py`, `INSTRUCTION`.
- **You type** — steps 3 and 4, with them. Twelve lines of English, no code.
- **Room does** — types it. No test on this block, by decision.
- **Say** — you are writing policy, not code. And the clause that feels redundant, check again when the reading did not change, is the entire reason anyone will see the agent think.
- **If it goes wrong** — nothing to go wrong. A typo in prose is harmless, which is why this block is the one under clock pressure.

### 0:30 — 0:31 · Cloud step two, submit the build

- **On screen** — terminal 2. Twenty seconds, then forgotten.
- **You type**
  ```
  IMAGE="$(terraform -chdir=infra output -raw image_repository)/agent:v1"
  gcloud builds submit --async --tag "$IMAGE" .
  ```
- **Room does** — the same. Write `IMAGE` on the state sheet.
- **Say** — this is the earliest minute the source is the finished source. A build submitted at 0:14 ships an unimplemented tool and fails in front of everyone at 0:41.
- **If it goes wrong** — `--async` means a failed build is silent until 0:39, and that is accepted. **Do not close terminal 2.** `IMAGE` lives only there and the apply at 0:40 needs it.

### 0:31 — 0:36 · The payoff

- **On screen** — terminal 1 restarting, then the browser.
- **You type**
  ```
  # Ctrl-C in terminal 1
  uv run adk web .
  ```
- **Room does** — restarts, re-uploads `04-halden-rigged-total.pdf`, 27 to 34 seconds.
- **Say** — narration **W2**, exactly as written. It is signed off as fixed wording, so it does not drift between runs, and it is reprinted here because flipping files mid-sentence costs more than the duplication:

  > Watch the trace as it fills in, not the spinner.
  >
  > It is doing the extraction first — that is the slow part, it is genuinely reading a PDF. Then it will call the arithmetic check, and the check will come back false.
  >
  > And what happens next is the entire workshop. It goes back to the document. Then it checks **again** — with numbers it already knows have not changed.
  >
  > That second call looks like a wasted call. It is the only reason you can see the agent think. If the instruction let it stop at the first false, this trace would be one line and none of us would know whether it looked twice or just gave up.

  No asides here and no questions taken. "Hold that, watch this first."
- **If it goes wrong** — **this is the one thing.** Every attendee confirms out loud they have two checks in their trace before the room moves on. Anyone with one check has an empty step 4; the fix is `cp solutions/agent.py invoice_agent/agent.py` and a restart.

### 0:36 — 0:39 · Slack

- **On screen** — whatever is up.
- **You type** — nothing.
- **Room does** — questions, catch-up, breath.
- **Say** — this block exists to be spent. First item on the cut list.
- **If it goes wrong** — it cannot.

### 0:39 — 0:44 · Collect the deploy

- **On screen** — terminal 2, then terminal 3, then the browser on `localhost:8080`.
- **You type**
  ```
  # 0:39
  gcloud builds list --limit 1

  # 0:40  — the -var is not optional
  terraform -chdir=infra apply -auto-approve -var "image=$IMAGE"

  # 0:41  — terminal 3, and it stays running for the rest of the hour
  gcloud run services proxy invoice-agent --region europe-west1 --project <DELIVERY_PROJECT>
  ```
- **Room does** — the same, then uploads the rigged invoice once more at 0:42, then opens `localhost:8080/records` at 0:43.
- **Say** — narration **W3** over the build check, then **W4** over the apply. The double check appears again, now writing to Firestore and archiving the PDF to Cloud Storage.
- **If it goes wrong** — `FAILURE` on the build is a synchronous rerun of `gcloud builds submit --tag "$IMAGE" .` while the room moves on. Do not read the log from the front. Dropping the `-var` redeploys Google's hello container over the agent; the symptom is a cheerful apply and a page that is not the developer UI.

### 0:44 — 0:49 · Teardown, live, together

- **On screen** — terminal 2.
- **You type**
  ```
  scripts/teardown.sh
  ```
- **Room does** — the same, on their own project. Read what it prints.
- **Say** — nobody leaves the room with something running. Then the split from [`COST.md`](COST.md): on the $300 free trial a surprise bill is structurally impossible, because Google closes a trial account rather than upgrading it. The $5 budget alert is for attendees on an existing paid billing account, and only them.
- **If it goes wrong** — **not cuttable.** Compressible to sixty seconds of "run this now, I will wait."

### 0:49 — 0:57 · What that was, and where it goes

- **On screen** — slide 5.
- **You type** — nothing.
- **Room does** — listens.
- **Say** — three points: a tool's description is its interface, English is the type signature; the interesting behaviour is in the loop, not the model; an agent you cannot watch is an agent you cannot trust, the trace was the product. Then the take-home.
- **If it goes wrong** — compresses from eight minutes to three. The take-home is in the README.

### 0:57 — 1:00 · Questions and the URL

- **On screen** — the last slide, repo URL and QR.
- **You type** — nothing.
- **Room does** — asks, scans.
- **Say** — the URL, recitable. The feedback ask.
- **If it goes wrong** — nothing left to lose.

### Cut list

Late is the normal case. Cut in this order and say nothing about it: slack at
0:36, the cloud run of the rigged invoice at 0:42, the wrap-up compressed to
three minutes, their own records page at 0:43, the clean-invoice run at 0:18.

**Never cut** fill-in two, the payoff, or the teardown. If the collection will
not fit before 0:44, abandon the collection.

---

## After the room

Same day, and the step most likely to be forgotten because the room is over.

```bash
cd ~/dev/adk-invoice-workshop
scripts/sandbox.sh --teardown
```

Then do the thing it tells you it did not do. A consumer `googlegroups.com`
group belongs to no Cloud Identity customer, so there is no CLI for its
membership and the UI is the API. Open the group's member page, select all,
remove members, and keep the group and its join policy. If you skip this, this
workshop's attendees are pre-granted on the next sandbox.

Also kill the sandbox proxy, still running minimized on 8081, and confirm the
delivery project is gone.

Then keep the pre-flight reports. The distribution of failures is the best data
you will get for running this again, and the version line ties a failure to an
exact commit of the kit.

---

## Aborts

Three room-wide failures. Each decision is made here because it cannot be made
at 0:32 with forty people watching.

**More than about a quarter of the room fails the apply at 0:14.** That is not
a diversion, that is the pre-flight having failed. Announce that everyone is on
the sandbox. Drop the second apply and the teardown from the plan. Say nothing
else about it, and do not spend the recovered ten minutes explaining what went
wrong.

**Conference wifi collapses.** The local half is untouched, because nothing
from 0:05 to 0:18 needs the network once `uv sync` has run and persistence
falls back to a file on disk. Abandon all three cloud blocks in **one**
announcement rather than discovering each of them separately, and say plainly
that the hour is now the local hour and the one thing still happens. The
recovered fifteen minutes go to the wrap-up and questions, not to retrying.
Your hotspot is for the projector and the sandbox, not for forty laptops.

**Vertex is slow.** Narrate longer and start cutting from the top of the cut
list immediately, before you are behind rather than after. Every measured
number in the kit came from one machine on good wifi; treat a first run at
double the budget as the new budget and re-plan on that.

**Vertex is down or quota-limited.** There is no local model fallback anywhere
in this kit and pretending otherwise would be the lie. The hour becomes a
walkthrough on your screen: the room still types both fill-ins, and you run the
rigged invoice yourself the moment anything answers. If nothing answers at all,
read a captured trace and teach the loop from it. Say what happened, once, and
do not apologise twice.

---

## Open

1. **The 0:31 restart.** This runbook says restart `adk web`, matching the run
   of show. [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15)
   is what answers it. If ADK reloads an edited `INSTRUCTION`, the block loses
   the Ctrl-C and gets a minute cheaper.
2. **The proxy at 0:41 is the largest unrehearsed step**, and it is the one
   this file cannot help with. [#22](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/22)
   reached the service on its `run.app` URL with a token, which is not the
   route the room takes.
3. **The sandbox proxy on 8081 is unproven** for the same reason as the
   delivery proxy, and it is load-bearing from the first sixty seconds rather
   than from 0:41.
4. **W1's `cd infra`** contradicts the terminal-2 rule above. Fix it in
   [`speaker-notes.md`](speaker-notes.md) rather than remembering it.
