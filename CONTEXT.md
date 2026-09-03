# ADK invoice workshop

A 60-minute hands-on workshop in which working engineers build a Google ADK
invoice-analyzer agent and deploy it to their own Google Cloud project. The
repo is both the agent and the kit for running the hour.

Eight documents share the vocabulary below. It is written down here because a
reader who picks up one of them has usually not read the other seven.

## The hour

**The one thing**:
The single outcome every attendee must leave having achieved — the re-read
typed, and their own agent calling the arithmetic check twice on the rigged
invoice. Locally counts; deploying does not.
_Avoid_: the goal, the takeaway, the payoff

**The payoff**:
The 0:31 segment where the rigged invoice runs against the completed
instruction and the double check appears in the trace. The event that proves
the one thing.
_Avoid_: the demo, the money shot

**Fill-in one**, **fill-in two**:
The only two things an attendee types. One is the `check_invoice_arithmetic`
tool and its docstring; two is steps 3 and 4 of the agent instruction. Always
numbered, never named by their file.
_Avoid_: exercise, lab, the gaps

**Gap**:
A region of a shipped file left deliberately unwritten, marked by a comment
fence that names the file and carries its own recovery `cp` command. There are
exactly two, one per fill-in.
_Avoid_: TODO, stub, placeholder

**Dead window**:
A stretch of the hour where a command is running and the room has nothing to
do. There are four, and each has narration written to fill it rather than
improvised.
_Avoid_: gap, pause, filler

**Cut list**:
The ordered sequence in which segments are abandoned when the hour runs late,
decided in advance so the decision is never made live.
_Avoid_: backup plan, if there is time

## People and routes

**Attendee**:
Anyone in the room. Has done the pre-flight and owns a Google Cloud project.
_Avoid_: participant, student, delegate

**Cold arrival**:
An attendee who reaches the room without a working pre-flight. Does the entire
local half hands-on using the sandbox as a model backend, and misses only the
three cloud blocks.
_Avoid_: latecomer, unprepared attendee, failure case

**The diversion point**:
0:14, the moment the first Terraform apply finishes and a failing attendee is
sent to the sandbox. The only scripted moment for redirecting someone, and the
only one with enough runway left.
_Avoid_: the fallback moment, triage

**Host**:
The person delivering the workshop. Owns the sandbox, the deck and the runbook.
_Avoid_: presenter, speaker, instructor

## Infrastructure

**Sandbox**:
A throwaway Google Cloud project the host creates on the morning of the
workshop and deletes the same day. Two affordances: a deployed service anyone
signed in can reach, and a model backend for agents running on cold arrivals'
own laptops.
_Avoid_: shared project, demo project, fallback environment

**Access group**:
The open-join Google Group granted two roles on the sandbox. A named identity
a stranger can put themselves inside, which is what project-level IAM accepts
where a wildcard is refused.
_Avoid_: allowlist, the group of attendees

**Live clone**:
The fresh clone at the pinned tag, in its own directory, that the host runs the
hour from. Distinct from the host's development checkout, which ships the
finished agent and cannot show a red test.
_Avoid_: demo repo, presentation copy

**State sheet**:
The block of per-delivery blanks at the top of the host runbook — sandbox
project id, tag, image URI, ports, counts. The only part of the runbook that
changes between deliveries.
_Avoid_: cheat sheet, notes

**Delivery project**:
The empty Google Cloud project the host creates the day before, runs the three
cloud blocks against, and tears down live at 0:44 with the room.
_Avoid_: my project, the demo project

**Pre-flight**:
The 30 minutes of setup every attendee does the day before, ending in one
script that prints a report block they send back.
_Avoid_: setup, prerequisites, onboarding

## The agent

**Rigged invoice**:
`04-halden-rigged-total.pdf`, whose stated total cannot be reconciled with its
lines by any reading. The designed failure the hour is built around.
_Avoid_: broken invoice, bad invoice, test case

**Re-read**:
The instruction's requirement to go back to the document after a failed
arithmetic check and then check a second time, even when nothing changed. The
second check is what puts the agent's thinking on screen.
_Avoid_: retry, correction, self-healing

**Validation**:
The arithmetic chain — every line's quantity times unit price equals its
printed amount, and the amounts sum to the printed total, to one cent. The
store decides `validation_passed`, not the agent.
_Avoid_: verification, checking, auditing
