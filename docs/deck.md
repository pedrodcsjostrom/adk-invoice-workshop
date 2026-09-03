# Deck — 60-minute ADK invoice workshop

**Status: reviewed by Peter, unrehearsed.** Ticket [#32](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/32). **Five slides.** Reads against [`run-of-show.md`](run-of-show.md); the narration for the dead windows is in [`speaker-notes.md`](speaker-notes.md).

This file is the **content**. [`deck.marp.md`](deck.marp.md) is a renderable Marp version of the same five slides, for looking at:

```
npx --yes @marp-team/marp-cli --no-stdin docs/deck.marp.md -o deck.pdf
npx --yes @marp-team/marp-cli --no-stdin docs/deck.marp.md --preview   # live
```

Marp is a convenience, not a commitment — retyping these five into Slides is twenty minutes. Do not build the real deck until the content survives [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15).

## Why five and not zero

The run of show names exactly one slide, at the open. That is nearly right and not quite: a few moments need something on screen that is not a terminal, and one of them is a moment where Peter is talking over a running command with nothing to point at. A deck of five earns its place; a deck of twenty would not.

**This started at six.** The sixth was a slide at 0:05 listing the two gaps and the gap-test command. Peter cut it: the same words spoken over the repo tour are enough, and a slide that only restates what is already fenced in the attendee's own file is a slide that has to be found, switched to and switched away from for no gain. Its content did not disappear — it moved into the 0:05 narration in [`speaker-notes.md`](speaker-notes.md), which is where it always belonged.

The cut has a second effect worth naming: **the loop slide is now the only slide that appears mid-hour at all.** Everything between 0:05 and 0:49 is a terminal and an editor, apart from twenty seconds at 0:14. That is a stronger position than six slides was, because the one time the projector changes, it means something.

## Why the escape hatch is not the constraint it looked like

The ticket treats the recovery `cp` as something that must be visible on the projector for the whole hour, which would rule out ever putting a slide up. It does not have to be. [#25](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/25) already put the recovery command inside the comment fence in the attendee's own file — so it is on **every attendee's own screen**, in the file they are editing, at the moment they need it. That is a better place than the projector: it is there when they look down, not when they look up.

**There are two of them, not one.** The run of show and this ticket both say "the escape hatch" singular and quote only the `tools.py` line. The fences on the attendee branch carry one each:

```
cp solutions/tools.py invoice_agent/tools.py     # fill-in one, needed from 0:09
cp solutions/agent.py invoice_agent/agent.py     # fill-in two, needed from 0:25
```

Belt and braces, three cheap additions:

- **Whiteboard.** Both lines, written at 0:05, never erased. Survives every screen switch.
- **Slide footer.** The loop slide carries both lines in small type. It is the only slide up while the gaps are live, and 0:14 is exactly when a lagging attendee needs the copy. The takeaways slide dropped its footer with the cut: by 0:49 the gaps are done, and a recovery command there is noise.
- **Pinned chat message**, if the room has a channel.

The projector is then free to show whatever the minute needs.

## Operational notes

- The deck is a **PDF open in its own window**, on a second workspace, alt-tab away. Not a browser tab that has to be found. The 0:14 switch is a keystroke.
- Slide 2 is shown twice: at 0:01 for cold arrivals and at 0:14 for the diversion. Same slide both times, deliberately — the second showing is meant to feel familiar.
- **The loop slide is the only one that appears mid-hour**, for about twenty seconds at 0:14. Slide 2 is reshown at the same moment for anyone diverting to the sandbox.

---

## Slide 1 — The promise · 0:00

> ### Build an agent that reads an invoice, catches one that does not add up, and files it anyway with a flag.
>
> **60 minutes. On your own Google Cloud project.**
>
> `bit.ly/adk-invoices`
> [ QR code — same URL ]

*On screen 0:00-0:01, then the live demo takes over. Back up at 0:57.*

---

## Slide 2 — Cold arrival / the sandbox · 0:01 and again at 0:14

> ### Pre-flight did not pass? Three lines and you are with us.
>
> **1 · Join the group** — `________@googlegroups.com` [ QR code ]
> Do this first. It takes a few minutes to reach IAM, and you have thirteen.
>
> **2 · Two lines in your `.env`:**
>
> ```
> GOOGLE_CLOUD_PROJECT=adk-sandbox-________
> GOOGLE_CLOUD_LOCATION=global
> ```
>
> **3 · Then authenticate:**
>
> ```
> gcloud auth application-default login
> gcloud auth application-default set-quota-project adk-sandbox-________
> ```
>
> **Now clone, and do everything the room does.**
> You skip only the three deploy steps. The part that matters is yours.

*Also printed as the handout — same content, same words, so the slide and the paper agree.*

**This slide was rewritten twice, and the second rewrite is the interesting one.**

The draft carried a `gcloud run services proxy` command and a reassurance that everything up to 0:39 ran on the attendee's laptop. [#13](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/13) falsified the reassurance — `allAuthenticatedUsers` is refused on a project-level IAM policy, so a cold arrival could not be granted Vertex and could not run an agent at all — and the line was deleted rather than reworded, because a comforting sentence would have hidden the hole rather than closed it.

[#37](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/37) then closed it properly, and the slide inverts. A **Google Group** is on the very list of member types #13's error message named as allowed, so an open-join group granted on the sandbox project makes it a *model backend* for an agent running on the attendee's own laptop. A cold arrival does the whole local half hands on, in lockstep with the room, and misses only the three cloud blocks. So the proxy command comes off this slide: it was the old plan's centrepiece, and under the new one a cold attendee never needs it.

**Two blanks, both filled in by hand on the day, neither ever committed.** The project id is regenerated per run by `scripts/sandbox.sh`, and the group address takes the same posture — an open-join group granted on the project is a live door for anyone who learns it.

**The quota-project line is not optional.** #37 checked the live role definition: `roles/aiplatform.user` carries 446 permissions and none of them is under `serviceusage`, so the group needs `roles/serviceusage.serviceUsageConsumer` as well, and the attendee needs the quota project set. Without either, they get a 403 at 0:18 — inside the segment this whole arrangement exists to protect.

**Timing is why the join is step one.** Group membership takes minutes to reach IAM. Triage is at 0:01 and the first model call is at 0:18, so the cushion is thirteen minutes of productive local work. That cushion is a gift of the local-first ordering rather than something designed for it, and it is still unmeasured — [#40](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/40) proves the path.

## Slide 3 — The loop · 0:14, over the first apply

> ### An agent is three things.
>
> **A model.** **Some tools.** **An instruction.**
>
> Run in a loop until it stops asking for tools.
>
> There is no fourth thing.

Footer: `cp solutions/tools.py invoice_agent/tools.py` · `cp solutions/agent.py invoice_agent/agent.py`

*Twenty seconds of the ~50-second apply window. Then switch to the editor and show `INSTRUCTION` as it ships. See W1 in the speaker notes.*

---

## Slide 4 — What that was · 0:49

> ### Three things to take away.
>
> **1 · A tool's description is its interface.** English is the type signature.
>
> **2 · The interesting behaviour is in the loop, not the model.** Nothing clever happened in any single call.
>
> **3 · An agent you cannot watch is an agent you cannot trust.** The trace was the product.

Footer: `cp solutions/tools.py invoice_agent/tools.py` · `cp solutions/agent.py invoice_agent/agent.py`

---

## Slide 5 — Where it goes · 0:57

> ### `bit.ly/adk-invoices`
> [ QR code ]
>
> The take-home is in the README.
>
> **Feedback:** [ TBD — link or QR ]

*Left up through questions until the room empties.*

---

## Open on the deck

1. ~~Slide 2's placeholders.~~ **Settled.** [#13](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/13) and [#37](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/37) between them decided what the slide says. Two blanks remain by design, the sandbox project id and the group address, both filled in by hand on the day and never committed. [#40](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/40) stands the group up and proves the path; until it does, the slide describes a route nobody has walked.
2. **Feedback capture** on slide 5 is unspecified — it is still in the map's fog.
3. ~~Whether the gaps slide earns its place.~~ **Cut.** Peter's call; the words moved into the 0:05 narration.
4. **QR codes are not generated.** Three now, not two: `bit.ly/adk-invoices` on slides 1 and 5, and the group join page on slide 2. The last one cannot be made until the group exists.
5. ~~"The escape hatch" is singular in the run of show.~~ **Corrected**, both lines now printed at 0:05.
6. ~~The Terraform directory.~~ **Corrected** to `infra/` in the notes and the outline. Found by checking the narration commands against [`DEPLOY.md`](DEPLOY.md), which also caught the missing `-var "image=$IMAGE"` on the second apply.
7. **Nothing here has been said out loud.** [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15) is the test, and it must walk the cold-arrival path as well as the main one.
