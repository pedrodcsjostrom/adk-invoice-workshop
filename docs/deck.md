# Deck — 60-minute ADK invoice workshop

**Status: rough, unreviewed, unrehearsed.** Ticket [#32](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/32). Six slides. Reads against [`run-of-show.md`](run-of-show.md); the narration for the dead windows is in [`speaker-notes.md`](speaker-notes.md).

This file is the **content**. [`deck.marp.md`](deck.marp.md) is a renderable Marp version of the same six slides, for looking at:

```
npx --yes @marp-team/marp-cli --no-stdin docs/deck.marp.md -o deck.pdf
npx --yes @marp-team/marp-cli --no-stdin docs/deck.marp.md --preview   # live
```

Marp is a convenience, not a commitment — retyping these six into Slides is twenty minutes. Do not build the real deck until the content survives [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15).

## Why six and not zero

The run of show names exactly one slide, at the open. That is nearly right and not quite: four moments need something on screen that is not a terminal, and three of them are moments where Peter is talking over a running command with nothing to point at. A deck of six earns its place; a deck of twenty would not.

## Why the escape hatch is not the constraint it looked like

The ticket treats the recovery `cp` as something that must be visible on the projector for the whole hour, which would rule out ever putting a slide up. It does not have to be. [#25](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/25) already put the recovery command inside the comment fence in the attendee's own file — so it is on **every attendee's own screen**, in the file they are editing, at the moment they need it. That is a better place than the projector: it is there when they look down, not when they look up.

**There are two of them, not one.** The run of show and this ticket both say "the escape hatch" singular and quote only the `tools.py` line. The fences on the attendee branch carry one each:

```
cp solutions/tools.py invoice_agent/tools.py     # fill-in one, needed from 0:09
cp solutions/agent.py invoice_agent/agent.py     # fill-in two, needed from 0:25
```

Belt and braces, three cheap additions:

- **Whiteboard.** Both lines, written at 0:05, never erased. Survives every screen switch.
- **Slide footer.** Slides 3, 4 and 5 carry both lines in small type. Slides 1, 2 and 6 do not — the gaps do not exist yet at 0:00 and no longer matter at 0:57.
- **Pinned chat message**, if the room has a channel.

The projector is then free to show whatever the minute needs.

## Operational notes

- The deck is a **PDF open in its own window**, on a second workspace, alt-tab away. Not a browser tab that has to be found. The 0:14 switch is a keystroke.
- Slide 2 is shown twice: at 0:01 for cold arrivals and at 0:14 for the diversion. Same slide both times, deliberately — the second showing is meant to feel familiar.
- Slides 4 and 5 are the only ones that appear mid-hour.

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
> **Project:** `TBD-#13`
> **Service:** `TBD-#13`
>
> ```
> gcloud config set project TBD-#13
> gcloud run services proxy TBD-#13 --region europe-west1
> ```
>
> No credentials, no keys. Sign in with the Google account you already have.
>
> **You will not miss the important part.** Everything up to 0:39 runs on your laptop.

*Blocked on [#13](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/13) for the real ids. Also printed as the handout — same content, same words, so the slide and the paper agree.*

---

## Slide 3 — The two gaps · 0:05

> ### You will type two things today.
>
> **1 · `check_invoice_arithmetic`** — a tool, ~15 lines. *The docstring is prompt text.*
>
> **2 · Steps 3 and 4 of `INSTRUCTION`** — twelve lines of English. *You are writing policy, not code.*
>
> Both are marked in the file. Both have a solution next to them.
>
> ```
> uv run pytest tests/test_gap_arithmetic.py
> ```
> **It is red. That is correct.**

Footer: `cp solutions/tools.py invoice_agent/tools.py` · `cp solutions/agent.py invoice_agent/agent.py`

*Up during the repo tour while forty people clone and run one command. Comes down at 0:09.*

---

## Slide 4 — The loop · 0:14, over the first apply

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

## Slide 5 — What that was · 0:49

> ### Three things to take away.
>
> **1 · A tool's description is its interface.** English is the type signature.
>
> **2 · The interesting behaviour is in the loop, not the model.** Nothing clever happened in any single call.
>
> **3 · An agent you cannot watch is an agent you cannot trust.** The trace was the product.

Footer: `cp solutions/tools.py invoice_agent/tools.py` · `cp solutions/agent.py invoice_agent/agent.py`

---

## Slide 6 — Where it goes · 0:57

> ### `bit.ly/adk-invoices`
> [ QR code ]
>
> The take-home is in the README.
>
> **Feedback:** [ TBD — link or QR ]

*Left up through questions until the room empties.*

---

## Open on the deck

1. **Slide 2's ids** are placeholders until [#13](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/13) stands the sandbox up.
2. **Feedback capture** on slide 6 is unspecified — it is still in the map's fog.
3. **Whether slide 3 earns its place.** It is the most cuttable of the six; the same words spoken over the repo tour may be enough. [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15) decides.
4. **QR code generation** is not done. Two of them, same URL.
5. **"The escape hatch" is singular in the run of show** and there are two. Worth a one-line correction to [`run-of-show.md`](run-of-show.md) at 0:05, where it currently prints only the `tools.py` line.
