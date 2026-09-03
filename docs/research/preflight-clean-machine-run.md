# The pre-flight, run on a machine that had never seen it

Issue [#35](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/35).
The pack from [#12](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/12)
was written and tested on the machine that wrote it, which is the one machine
where it cannot fail for the reasons it exists to catch. This records what
happened on a machine with no gcloud, no config, no ADC, no clone, no Terraform
provider cache and — as it turned out, importantly — no Python at all.

**What was used.** A bare `ubuntu:24.04` container, following `docs/PREFLIGHT.md`
top to bottom. This settles everything that is a property of the *machine*. It
does not settle anything that needs a Google account: creating a project,
linking billing, `gcloud auth application-default login`, and therefore the
model check in section 7 and a proxy tunnel to a live private service. Those
still need a second person, and the checklist at the end of this file is what
they should run.

## What it broke, and what changed

### The script failed a machine that was fine

`python3` is not on a bare Ubuntu, and the script probed for exactly that. It
reported **"python3 is not installed"** and NOT READY on a machine where `uv
sync` had installed CPython 3.14.7, the dependencies resolved, and `adk web`
served the agent. The kit is run entirely through `uv`, and `uv` fetches its own
interpreter, so a system Python is one way to satisfy the requirement and not
the only one.

The check now looks at every interpreter the kit could actually use — `python3`,
the kit's own `.venv`, and whatever `uv python find` reports — and keeps the
newest. It prints which one it found: `python 3.14.7 — an interpreter uv
manages`. The install table in `PREFLIGHT.md` now says the Python row can be
skipped outright.

This is the defect the ticket existed to catch. Every attendee on a machine
without a system `python3` would have sent a NOT READY report for no reason.

### The developer-UI check fires later than the doc implied

The check looks for `invoice_agent/.adk`, ADK's per-agent session store. The
suspicion in the ticket was that a fresh ADK version might have moved it. It has
not moved — but it appears later than the doc assumed.

Starting `adk web`, hitting the server and stopping it again creates
**nothing**. The directory and its `session.db` appear only when a session is
first created, which is the moment you pick the agent from the dropdown in the
UI. So `PREFLIGHT.md`'s old instruction — "answer the dialog, look at the UI,
then stop it with Ctrl-C" — did not reliably satisfy `PREFLIGHT.md`'s own check.
Both the doc and the script's remedy now say to pick `invoice_agent` from the
dropdown, and say why.

Worth recording separately: the telemetry consent dialog is served from the
browser bundle, not written to disk. It is per-browser state and **no shell
script can detect it**. The marker is a proxy for "you opened the UI", which is
the best a script can do, and the two coincide as long as the attendee actually
picks the agent.

### Two smaller things a clean run exposes and a warm one cannot

- With no project selected, the credentials remedy printed a pasteable
  `gcloud config set project (none)`. It now prints `YOUR_PROJECT_ID`.
- Section 3 rendered as an empty heading when the project did not resolve, while
  every other downstream section explained itself. It now says it was skipped.

## What the run confirmed

**`sudo apt-get install google-cloud-cli-cloud-run-proxy` works.** This was the
ticket's first question and the answer is unambiguous. On an apt-installed
gcloud, `gcloud components install cloud-run-proxy` refuses — and refuses
*helpfully*, printing the exact apt command to run instead. The package installs
in about ten seconds, is 7 MB, and drops a real 20 MB binary at both
`/usr/bin/cloud-run-proxy` and `$SDK_ROOT/bin/cloud-run-proxy`. All three of the
script's detection branches then fire: the `$SDK_ROOT/bin` path exists, `gcloud
components list --only-local-state` lists `cloud-run-proxy`, and `dpkg -s`
succeeds. `gcloud run services proxy` resolves, prints help, and gets as far as
demanding credentials.

What is **not** proved is a tunnel to a live private Cloud Run service, which
needs a deployed service and a signed-in account. `#22` reached the service with
an identity token rather than through the proxy, and `#15` still owes that
rehearsal.

**The warnings are as described.** Exactly two `UserWarning: [EXPERIMENTAL]`
lines on startup, both harmless, matching the doc.

**The script does not crash on a machine where everything fails.** Eight
failures, one warning, exit 1, every remedy a runnable command.

## Is 30 minutes honest?

Yes, but the doc's reason for it was wrong. It said "most of it waiting on
downloads". Measured on a fast connection:

| step | time | size |
|---|---|---|
| `google-cloud-cli` via apt | 34s | 82 MB |
| `google-cloud-cli-cloud-run-proxy` | 10s | 7 MB |
| `terraform` via apt | 9s | 34 MB |
| `uv` install script | 2s | small |
| `git clone` of the kit | 1s | small |
| `uv sync` | 5s | 106 MB on disk |
| `terraform -chdir=infra init` | 4s | 126 MB on disk |
| **all of section 1** | **74s** | |
| **clone plus both warm-ups** | **39s** | |

About 250 MB of download. On a poor home connection that is a few minutes, not
half an hour. What actually fills the thirty minutes is the free-trial signup
with a payment card, two browser OAuth flows, and the **mandatory ten-minute
wait** for API enablement in step 3 — a third of the budget on its own, and the
one part no amount of bandwidth shortens. `PREFLIGHT.md` now says this, and
tells the reader to start step 3 early and do the rest while it settles.

## The bash 3.2 question, settled

The shell half of the macOS worry is now closed. GNU bash 3.2.0 was built from
source in a container and the whole script run under it, on a machine with no
gcloud, no terraform, no uv and no Python.

The hazard is real. Under `set -u`, bash 3.2 treats an expansion of an empty
array as an unbound variable and dies:

```
$ A=(); printf '%s\n' "${A[@]}"
line 7: A[@]: unbound variable
```

The guard is not. `${#A[@]}` on the same empty array is fine in 3.2 and
returns `0`, which is what every one of the script's thirteen array expansions
sits behind — either `[[ ${#A[@]} -gt 0 ]]` before the expansion, or the `else`
arm of `-eq 0`, where the array cannot be empty. The full run confirms it: the
script reaches its report block, prints `fix yourself:` and `warnings:`, and
correctly prints no `needs an admin:` section, which is the empty-array branch
being taken rather than avoided. Exit was clean with no unbound-variable error
anywhere.

So the script is safe on the bash every Mac ships. What that does **not** cover
is BSD userland, which is a different question from the shell version, and it
turned up one real defect.

### `mktemp` with no template, in the check that matters most

Section 7 opened its response buffer with a bare `body=$(mktemp)`. GNU coreutils
allows that; BSD `mktemp`, which is what macOS ships, wants a template. When it
refuses, `body` is empty, `curl -o ""` cannot write, `$code` comes back empty,
and the model check falls through to its catch-all arm — so a Mac attendee whose
machine is perfect gets NOT READY on the one check that proves the hour works,
under a message reading `the model call failed with HTTP` with nothing after it.

This is the same shape as the `python3` bug above: the script failing a machine
that is fine. It is now `mktemp "${TMPDIR:-/tmp}/preflight.XXXXXX"`, which both
implementations accept. Verified equivalent on Linux; the macOS failure is
inferred from BSD `mktemp` requiring a template, not observed on a Mac.

### `sort -V`, still open

`at_least()` compares versions with `sort -V`, and that flag is a GNU extension
that BSD sort has picked up only recently. It is left alone rather than guessed
at, because a wrong rewrite silently mis-compares every version in the script.
One command on any Mac settles it:

```
printf '2\n10\n' | sort -V | head -1     # prints 2 if -V works, 10 if it does not
```

If that prints `10`, `at_least` is broken on macOS and the gcloud, terraform and
Python version checks are all unreliable there.

## Not covered here

- **macOS end to end, and Windows.** No Mac was run. The shell is settled above
  and one BSD defect is fixed, but the `dpkg` branches of the proxy check are
  Linux-only, so a macOS attendee falls through to the generic remedy, which is
  right for the tarball SDK and unverified for Homebrew. `sort -V` is untested.
- **`tests/test_gap_arithmetic.py`** does not exist on this branch — it arrives
  with [#25](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/25)
  in PR #29. The script guards for its absence and skips. `PREFLIGHT.md`'s "you
  will see one test failing" becomes true once both branches land on `main`.

## What still needs a second person

Everything below the machine. One person with their own Google account, on a
laptop that has never seen this repo, following `docs/PREFLIGHT.md` end to end
against a brand-new project:

1. Sections 1 to 8 in order, noting the wall-clock time at each one.
2. Confirm the ten-minute API wait is enough, and that the marker file in step 3
   makes the script's "enabled N minutes ago" message appear as intended.
3. Confirm the report reads **READY**, with the model check in section 7 green —
   the only check that proves the whole path rather than inferring it.
4. Note any remedy line that did not actually fix what it claimed to.

That report is what closes #35.
