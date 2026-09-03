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

> ### Pre-flight did not pass? Use the sandbox.
>
> **Project:** `adk-sandbox-________`
> **Service:** `invoice-agent` **Region:** `europe-west1`
>
> ```
> gcloud auth login
> gcloud run services proxy invoice-agent \
>   --region europe-west1 --project adk-sandbox-________
> ```
>
> Then open `http://localhost:8080`.
>
> No credentials, no keys. Sign in with the Google account you already have.

*Also printed as the handout — same content, same words, so the slide and the paper agree.*

**[#13](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/13) has landed, and it changes this slide twice.**

The service name and region are fixed and can be printed now; only the project id is a blank, because the repo is public and the id is the only thing standing between it and an open Gemini budget. `scripts/sandbox.sh` generates it with a random suffix on the morning of the workshop and prints the handout block this slide copies. **Fill the blank in by hand on the day.** The slide file must never be committed with a real id in it.

The reassurance that was here has been **removed, not reworded**: *"You will not miss the important part — everything up to 0:39 runs on your laptop."* That is false as built. `allAuthenticatedUsers` is refused on a project-level IAM policy, so a cold attendee cannot be granted Vertex access on the sandbox project and therefore cannot run `adk web` at all. They reach Peter's already-built agent through the proxy and watch the payoff instead of producing it — which is exactly the one thing [#11](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/11) says every attendee must leave having done. **[#37](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/37) owns that decision, and this slide cannot be finished before it lands.** Writing a comforting line here would only hide the hole.

One practical note worth a footer or a spoken aside: the proxy needs a component that is a separate package on an apt gcloud, `sudo apt-get install google-cloud-cli-cloud-run-proxy`. [#12](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/12) established it is installable after all, correcting the write-off in [#8](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/8) and [#22](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/22), and the pre-flight now checks for it — so this should only ever bite a genuinely cold arrival, which is precisely the person looking at this slide.

---

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

1. **Slide 2 is blocked on [#37](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/37)**, not on [#13](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/13) any more. #13 gave it the service name and region; what it still lacks is an honest answer to what a cold attendee actually *does*. The project id is a deliberate day-of blank and is not an open question.
2. **Feedback capture** on slide 5 is unspecified — it is still in the map's fog.
3. ~~Whether the gaps slide earns its place.~~ **Cut.** Peter's call; the words moved into the 0:05 narration.
4. **QR code generation** is not done. Two of them, same URL.
5. **"The escape hatch" is singular in the run of show** and there are two. Worth a one-line correction to [`run-of-show.md`](run-of-show.md) at 0:05, where it currently prints only the `tools.py` line.
6. **The Terraform directory is `infra/`, not `terraform/`.** Found while checking the narration commands against [`DEPLOY.md`](DEPLOY.md). The repo tour at 0:05 and the run of show both said `terraform/`, and W1's script said `cd terraform`. Corrected in the notes and the outline; nothing on the slides themselves named it.
