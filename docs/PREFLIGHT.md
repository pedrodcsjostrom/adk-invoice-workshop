# Pre-flight — do this the day before

The workshop is 60 minutes and every one of them is spoken for. None of them
are available for installing Terraform, waiting for a Google Cloud API to
switch on, or discovering that your laptop cannot reach the model. So all of
that happens today, on your own machine, before you arrive.

Budget **30 minutes**. The downloads are only a few minutes of that — about
250 MB in total, and step 5 tells you why they still have to happen today. What
actually fills the half hour is signing up for the free trial, two browser
sign-ins, and one **unavoidable ten-minute wait** in step 3 while Google turns
the APIs on. Start step 3 early and do the rest while it settles.

At the end you run one script and send its output to the host. That report is
the whole point of this page: if it says READY, tomorrow works.

You need a laptop you can install software on, a Google account, and a payment
card. The card is for Google's free trial, which is what pays for the hour —
about **20 cents** of Gemini tokens per person, and nothing else. If you are on
a trial, Google cannot bill you: it closes a trial account rather than charging
it. [docs/COST.md](COST.md) has the detail, including the one case that needs a
budget alert.

---

## 1. Install five things

| | Why | Where |
|---|---|---|
| `gcloud` | Everything Google Cloud | <https://docs.cloud.google.com/sdk/docs/install> |
| `terraform` 1.5+ | You create your own cloud stack during the hour | <https://developer.hashicorp.com/terraform/install> |
| `python` 3.10+ | The agent | your package manager — or skip it, `uv sync` in step 5 fetches its own |
| `uv` | Installs the agent's dependencies in seconds | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `git` | Cloning the kit | your package manager |

Then the sixth thing, which is the one people miss:

```bash
gcloud components install cloud-run-proxy
```

The agent you deploy is **private** — there is no public URL, by design. The
only way you open it is through this proxy. If `gcloud` came from a package
manager it will refuse the command above, because it does not own its own
components — but it refuses helpfully, printing the exact command to run
instead. On Debian or Ubuntu that command is:

```bash
sudo apt-get install google-cloud-cli-cloud-run-proxy
```

That package is real, it is in the repository Google already ships, and it
installs a working proxy — the check script in step 7 confirms it three
different ways.

If `gcloud` came from snap, it cannot take components at all. Remove it and
install the tarball SDK from the link in the table.

**No password on this machine?** The tarball SDK is the way out, and it is
quicker than it sounds: it unpacks into your home directory and takes the
component in about nine seconds, with no root at all.

```bash
curl -sSLO https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
tar -xzf google-cloud-cli-linux-x86_64.tar.gz
./google-cloud-sdk/bin/gcloud components install cloud-run-proxy
```

It shares your existing sign-in, so there is nothing to log in to again. The one
trap, and gcloud will warn you about it: you now have **two** installations, and
the old one still has no proxy. Put the new `google-cloud-sdk/bin` first on your
`PATH`, or call it by full path every time. Getting this wrong looks exactly
like the component failing to install.

## 2. Make a project, and link billing

One project, used only for this workshop, so that deleting it afterwards costs
you nothing. In the [console](https://console.cloud.google.com/projectcreate),
or:

```bash
gcloud projects create my-invoice-workshop --name="Invoice workshop"
```

Then **link a billing account** to it, on the
[billing page](https://console.cloud.google.com/billing/linkedaccount). This is
not optional and it is not about the money: an unlinked project cannot use
Google Cloud at all, free tier included.

If your employer's Google account is the one you are using, read
[section 8](#8-if-this-is-a-corporate-account) first. It may be quicker to use
a personal account.

## 3. Turn the APIs on, and then wait

Eight APIs, one line. Do this **at least ten minutes** before you run the check
script, because enablement takes a few minutes to propagate and it is slowest
on a project you just created.

```bash
export PROJECT_ID=my-invoice-workshop

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  compute.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project="$PROJECT_ID"

mkdir -p ~/.config/adk-workshop && date +%s > ~/.config/adk-workshop/apis-enabled-at
```

That last line records when you did it, so the check script can tell you to
wait rather than letting you believe a propagation delay is a broken project.

Terraform does not enable these tomorrow. It cannot: enabling an API and using
it in the same apply is the single most common way this kind of stack fails.

## 4. Sign in — the order of these two commands matters

```bash
gcloud config set project "$PROJECT_ID"
gcloud auth application-default login
```

The first line is what makes the second one record a *quota project* in your
saved credentials. Run them the other way round and tomorrow's apply stops with
an error about a missing quota project.

If your shell profile sets `GOOGLE_APPLICATION_CREDENTIALS`, unset it. It
silently overrides everything you just did.

## 5. Get the kit, and warm it up

```bash
git clone https://github.com/pedrodcsjostrom/adk-invoice-workshop.git
cd adk-invoice-workshop

cp invoice_agent/.env.example invoice_agent/.env
# edit invoice_agent/.env and set GOOGLE_CLOUD_PROJECT to your project id

uv sync                        # installs the agent's dependencies
terraform -chdir=infra init    # puts the Terraform provider on disk
```

Both of those downloads are load-bearing. Forty laptops pulling the ADK and the
Google provider simultaneously over conference wifi is not a plan, and there is
no slack in the hour for it.

Do not `git pull` tomorrow morning. If a fix goes out overnight the host will
say so from the front of the room and it will be a fresh clone, never a pull
into a working copy you have started typing in.

## 6. Run the developer UI once

```bash
uv run adk web .
```

Open <http://127.0.0.1:8000> and **pick `invoice_agent` from the dropdown at the
top left**. Do not skip that part: choosing the agent is what creates the local
session store, and it is what the check script looks for. Starting the server
and stopping it again leaves no trace, and the check will still warn at you.

The first launch also shows a telemetry consent dialog and prints two alarming
warnings that are harmless. Answer the dialog, look at the UI, then stop the
server with Ctrl-C. Getting this out of the way today is worth two minutes of
the room's time tomorrow.

You will also see one test failing if you run the suite. That is deliberate —
the kit ships with two gaps in it that you fill in during the session.

## 7. Run the check, and send the report

```bash
./scripts/preflight_check.sh
```

It checks about thirty things and takes a few seconds. It changes nothing,
apart from asking Gemini to say "ping" — the one check that proves the entire
path end to end rather than inferring it.

It ends with a block like this:

```
================= PRE-FLIGHT REPORT =================
RESULT      : READY
...
=====================================================
```

**Send that whole block to the host today**, whatever it says. A NOT READY sent
today is a solved problem; a NOT READY discovered tomorrow at 0:14 costs you a
third of the workshop. Anyone who arrives without a working project gets a
shared sandbox instead and runs one segment behind, which works, but it is not
the version of the hour you want.

Every failure the script reports comes with the command that fixes it. Two are
worth knowing in advance:

- **needs an admin** means an organization policy or a missing role on your
  project. Nothing you type will fix it. Forward the report to whoever runs
  your cloud, or switch to a personal account.
- **APIs enabled only N minutes ago** is not a failure. Wait, re-run.

## 8. If this is a corporate account

Projects under a company organization inherit policies you cannot change. The
kit is built to survive the usual ones — the deployed service is private, and
no service account key is ever created — so most corporate attendees are fine.
The check script reads your effective policies and tells you which ones bite.

Two cases genuinely block you: a policy that restricts which regions you may
use, and not holding Owner on your own project. Both need your admin, and both
are worth discovering today rather than tomorrow.

## What to have ready tomorrow

- The clone, opened in your editor.
- **Three terminals** in that directory. You will need all three at once late in
  the hour: one running the agent, one for gcloud and Terraform, one for the
  proxy.
- Your project id somewhere you can paste from.
- The workshop is hands-on from minute five. Nothing else to prepare.
