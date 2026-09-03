# Speaker notes — the four dead windows and the diversion

**Status: rough, unreviewed, unrehearsed.** Ticket [#32](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/32). Companion to [`run-of-show.md`](run-of-show.md) and [`deck.md`](deck.md).

The hour deliberately runs commands under talking. Four windows are long enough that improvising over them will show. Each script below is written to be **said**, not read — spoken at a normal pace, the word counts land inside the measured wait. Each has a **short tail** to drop if the command finishes early and a **stretch** if it runs long.

Timings in brackets are the measured numbers from [#22](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/22). None of this has been said out loud yet; [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15) is what turns these budgets into measurements.

---

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

**The line, said once, to the whole room** — *provisional, and the second sentence is currently untrue; see the warning below:*

> If your apply just failed — do not debug it now. Come and use the sandbox. It is on the slide, it takes about three minutes, and you will not miss anything that matters: everything between here and 0:39 runs on your laptop.

> [!WARNING]
> **Do not say the second half of that line until [#37](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/37) lands.**
> [#13](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/13) stood the sandbox up and found that the reassurance is false as built. `allAuthenticatedUsers` is refused on a project-level IAM policy, so a cold attendee cannot be granted Vertex on the sandbox project and cannot run `adk web` against it. What "everything runs on your laptop" was promising — that they build their own agent and only the *deploy* is borrowed — is exactly what the sandbox cannot give them. They reach Peter's finished agent through the proxy and watch.
>
> The hole is real and it is the hour's one mandatory exercise, so the fix is a decision, not a form of words. Until #37 answers it, say only the first half: do not debug now, come and use the sandbox.

**What goes on screen:** slide 2, the same slide they saw at 0:01. Project id, service name, two commands, no credentials. Showing the *same* slide is the point — it should read as a planned route, not a rescue.

**The rules, for Peter:**

1. **Do not debug an individual project from the front.** Not once. The slide is the help.
2. **Do not ask what the error was.** It invites a diagnosis in front of forty people. The sandbox works regardless of the error.
3. **Keep moving.** The room continues to 0:18 on schedule; the diverted attendee catches up during the first run, which is local and needs nothing from the cloud.
4. **If more than about a quarter of the room fails**, that is not a diversion, that is the pre-flight having failed — announce that everyone is on the sandbox, and drop the second apply and the teardown from the plan. Say nothing else about it.
5. **A helper**, if one is available, takes the diverted attendees at the back. If not, the slide does.

**The thing that makes this survivable** is already true and worth saying out loud once at 0:14: the payoff is local. A cloud failure at this point costs a deployment, not the workshop.

---

## Open on the notes

1. **None of this has been said out loud.** The word counts are estimates against measured command times. [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15) is the test.
2. **W4 assumes the proxy step follows immediately.** The run of show flags the proxy path as its largest unproven hole; if it needs its own narration window, this is where it lands.
3. **The 86x figure** comes from `docs/COST.md` — check it still says that before saying it in a room.
4. **There are two recovery `cp` commands**, one per fence, and the run of show names only the `tools.py` one. Small correction to make there.
5. **No narration is written for 0:18**, the first `adk web` launch. The run of show budgets seven minutes there for friction, which is attendee time rather than a dead window, but forty people hitting a telemetry consent dialog at once may want a scripted line too.
6. **The Terraform directory is `infra/`.** W1 said `cd terraform`, which does not exist. Corrected above and in the run of show.
7. **The proxy component is installable after all.** [#12](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/12) found `google-cloud-cli-cloud-run-proxy` is a package in the repo Google already ships, reopening the route [#8](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/8) and [#22](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/22) wrote off. The pre-flight now checks for it, so W4's stretch line about the proxy stands and note 2 above is smaller than it was — but the path is still unrehearsed, which is [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15).
