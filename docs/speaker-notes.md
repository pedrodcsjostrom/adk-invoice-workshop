# Speaker notes — the four dead windows and the diversion

**Status: reviewed by Peter, unrehearsed.** Ticket [#32](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/32). Companion to [`run-of-show.md`](run-of-show.md) and [`deck.md`](deck.md).

The hour deliberately runs commands under talking. Four windows are long enough that improvising over them will show. Each script below is written to be **said**, not read — spoken at a normal pace, the word counts land inside the measured wait. The 0:05 section is the exception: it is not a dead window, it is the narration that replaced a cut slide, and it is not racing a command. Each has a **short tail** to drop if the command finishes early and a **stretch** if it runs long.

Timings in brackets are the measured numbers from [#22](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/22). None of this has been said out loud yet; [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15) is what turns these budgets into measurements.

---

## 0:05 — naming the two gaps, with nothing on screen

Not a dead window: the room is looking at the repo, not a spinner. It is here
because the deck had a slide for this and Peter cut it, and the words are worth
keeping. Say it over the repo tour, projector on the editor.

> You are going to type two things today. That is all — the rest is already
> written, and most of it is plumbing you would not learn anything from typing.
>
> The first is a tool called `check_invoice_arithmetic`. About fifteen lines.
> The thing to notice while you write it is that its **docstring is prompt
> text** — it is not a comment, it is the only description the model ever sees
> of what this function is for. You are writing the interface in English.
>
> The second is steps three and four of the instruction. Twelve lines of prose.
> No code at all. You are writing policy.
>
> Both are marked in the file with a fence you cannot miss, and both have the
> finished version sitting next to them in `solutions/`. The copy command is in
> the fence itself, so you never have to ask me for it, and it is on the
> whiteboard as well.

Then everyone runs the one command:

```
uv run pytest tests/test_gap_arithmetic.py
```

> It is red. That is correct. It stays red until the first thing you type, and
> going green is how you will know you are done — it takes about five seconds
> and it is the only test in the hour.

**Why this has no slide.** It restates what is already fenced in every
attendee's own file, and putting it on the projector costs a switch to and a
switch away for nothing. Leaving the editor up means the fences are on screen
while they are being described, which the slide could not do.

## W1 · 0:14 — over the first `terraform apply` [38s, budget ~50s]

Command first, then talk. Do not narrate the typing.

```
cd infra && terraform apply -auto-approve
```

> Leave that running. Don't watch it — it takes about forty seconds and nothing in it depends on a single thing you have typed. That is deliberate. It is the reason this step is here in the middle and not at the end.
>
> While it goes: if your gap test is still red, copy the solution file now. The command is in the comment at the top of `tools.py` — every gap in this repo carries its own recovery line, so you never have to ask me for it.

**[switch to slide 4 — the loop]**

> Here is the whole idea, and it is smaller than people expect. An agent is three things. A model. A set of tools. An instruction. You run it in a loop until it stops asking for tools. That is it. There is no fourth thing.

**[switch to the editor, `INSTRUCTION` on screen]**

> This is our instruction as it ships. Steps one and two, then five through eight. Three and four are empty — you can see the fence. So right now the agent extracts the invoice, checks the arithmetic once, and saves whatever it got. Hold that thought for ten minutes.

**[check the terminal]**

> Green? Nine resources. You now have a Cloud Run service running Google's hello container, which is the least interesting thing you will deploy today and exactly the point — it exists so the second apply has something to replace.

**Tail to drop if the apply finishes early:** the last paragraph. Say "green, nine resources" and move on.

**Stretch if it runs long:** *"`terraform init` already ran in your pre-flight, which is why this is forty seconds and not four minutes of provider download over conference wifi, forty times at once."*

**Then, immediately, the diversion — see below.**

---

## W2 · 0:31 — over the rigged-invoice payoff run [27-34s, budget ~30s]

This is the best thirty seconds of the hour and the only window where the narration is doing teaching work rather than filling time. Say it the same way every time.

**Peter has signed this one off as written** ([#32](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/32)), so treat the wording below as fixed rather than as a draft. It is the one script in the kit that should not drift between runs.

> Watch the trace as it fills in, not the spinner.
>
> It is doing the extraction first — that is the slow part, it is genuinely reading a PDF. Then it will call the arithmetic check, and the check will come back false.
>
> And what happens next is the entire workshop. It goes back to the document. Then it checks **again** — with numbers it already knows have not changed.
>
> That second call looks like a wasted call. It is the only reason you can see the agent think. If the instruction let it stop at the first false, this trace would be one line and none of us would know whether it looked twice or just gave up.

**[the trace lands]**

> There. Two checks, the re-read between them, and then it saves — with every number exactly as printed on the invoice.

**Tail to drop:** the last line; the run of show reads the trace together straight after anyway.

**Stretch:** *"And notice the store is the thing that decided `validation_passed` is false. Not the agent. The agent reports what it found; something else decides what that means."*

**Rule:** do not fill this window with anything else. No asides, no questions taken. If the room asks something, "hold that, watch this first."

---

## W3 · 0:39 — over the build check [~10-15s]

Short, and its job is to stop a failed build from becoming a group debugging session.

```
gcloud builds list --limit 1
```

> One command, and it either landed or it did not.
>
> `SUCCESS` and you are deploying in about a minute. `FAILURE` and — do not read the log from the front of the room, and do not panic. You rerun `gcloud builds submit` without `--async`, it takes under a minute, and you rejoin us. The part of the hour that matters already happened on your laptop.

**Stretch if the room is quiet and ahead:** *"This was submitted nine minutes ago with `--async`, which is why it is done. Had it streamed logs it would have held that terminal through the best five minutes of the session."*

---

## W4 · 0:40 — over the second apply and the container start [29s + 11s, budget ~40s]

Two facts, one per wait. Both are things attendees will actually hit next week.

```
terraform apply -auto-approve -var "image=$IMAGE"
```

The `-var` is not optional and is easy to drop under pressure: without it the
image falls back to its default and the apply cheerfully redeploys Google's
hello container over the agent. `IMAGE` was set before the build at 0:30 —
`IMAGE="$(terraform output -raw image_repository)/agent:v1"` — so it is still
in the shell unless the terminal was replaced. See [`DEPLOY.md`](DEPLOY.md).

> Twenty-nine seconds. It is replacing one revision — the image swaps, nothing else in the stack changes.
>
> Two things worth saying while it goes.
>
> First: `min_instance_count` is zero. That one number is the difference between this costing you nothing overnight and costing you real money — call it eighty-six times the idle bill. Scaling to zero means a cold start on the first request, and for a workshop, an internal tool, or anything you are still building, that is the trade you want.
>
> Second: this service runs as its own service account, not the Compute Engine default. The default has editor on your entire project — every service you deploy that way can delete every other thing you own. Ours can write to one Firestore database and one bucket, and that is the complete list. It is one Terraform block, and it is the cheapest security decision in the whole stack.

**[apply completes]**

> Revision replaced. Give it about ten more seconds before it answers — that is the container starting for the first time.

**Tail to drop:** the second fact. Keep `min_instance_count`; it is the one that saves them money.

**Stretch:** *"And the service is private. There is no public URL anywhere in this kit — no `allUsers`, nothing you could accidentally leave open. Which is why the next thing we run is a proxy."*

---

## The diversion — what the room sees when one attendee fails

The named diversion point is **0:14**, the moment the first apply finishes. It is also the only moment in the hour where one person's broken project can eat everyone else's time, so it is scripted rather than handled.

**The line, said once, to the whole room:**

> If your apply just failed — do not debug it now, and do not worry about it.
> There is a sandbox, it is on the slide, and it takes about three minutes.
> Join the group first, before anything else, because that is the part that
> has to travel. Then the two `.env` lines and the login, and you are doing
> exactly what everyone else is doing. You will miss the deploy at the end.
> You will not miss the part this hour is actually about.

**Say the last two sentences.** They are true now and they were not in the
draft. [#13](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/13) found that a cold arrival could not run an agent at all, and
[#37](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/37) fixed it with an open-join Google Group granted on the sandbox project
— which turns the sandbox from a service they watch into a **model backend for
the agent on their own laptop**. They are in lockstep with the room from 0:05
and diverge only at the three cloud blocks.

**Do not soften "you will miss the deploy".** It is a real loss and it should
be said out loud here rather than discovered at 0:40. Naming it costs four
words and buys the rest of the sentence its credibility.

**What goes on screen:** slide 2, the same slide they saw at 0:01 — the group address, the two `.env` lines, the login. Showing the *same* slide is the point: it should read as a planned route, not a rescue.

**The rules, for Peter:**

1. **Do not debug an individual project from the front.** Not once. The slide is the help.
2. **Do not ask what the error was.** It invites a diagnosis in front of forty people. The sandbox works regardless of the error.
3. **Keep moving.** The room continues to 0:18 on schedule. The diverted attendee catches up during the first run, which is local, and their group membership is propagating through exactly that window — thirteen minutes of cushion between the join at 0:01 and the first model call at 0:18. If they are still 403 at 0:18, that is the per-email fallback: one `add-iam-policy-binding` on the sandbox project, effective the moment it returns.
4. **If more than about a quarter of the room fails**, that is not a diversion, that is the pre-flight having failed — announce that everyone is on the sandbox, and drop the second apply and the teardown from the plan. Say nothing else about it.
5. **A helper**, if one is available, takes the diverted attendees at the back. If not, the slide does.

**The thing that makes this survivable** is already true and worth saying out loud once at 0:14: the payoff is local. A cloud failure at this point costs a deployment, not the workshop — and after #37, that is true of the cold arrival too, not just of the attendee whose apply failed halfway.

---

## Open on the notes

1. **None of this has been said out loud.** The word counts are estimates against measured command times. [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15) is the test. W2's *wording* is settled; its *timing* is not.
2. **W4 assumes the proxy step follows immediately.** The run of show flags the proxy path as its largest unproven hole; if it needs its own narration window, this is where it lands.
3. **The 86x figure** comes from `docs/COST.md` — check it still says that before saying it in a room.
4. **There are two recovery `cp` commands**, one per fence, and the run of show names only the `tools.py` one. Small correction to make there.
5. **No narration is written for 0:18**, the first `adk web` launch. The run of show budgets seven minutes there for friction, which is attendee time rather than a dead window, but forty people hitting a telemetry consent dialog at once may want a scripted line too.
6. **The Terraform directory is `infra/`.** W1 said `cd terraform`, which does not exist. Corrected above and in the run of show.
7. **The proxy component is installable after all.** [#12](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/12) found `google-cloud-cli-cloud-run-proxy` is a package in the repo Google already ships, reopening the route [#8](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/8) and [#22](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/22) wrote off. The pre-flight now checks for it, so W4's stretch line about the proxy stands and note 2 above is smaller than it was — but the path is still unrehearsed, which is [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15).
