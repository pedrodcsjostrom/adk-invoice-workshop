# The pre-flight email, and how to read what comes back

Host-facing. [docs/PREFLIGHT.md](PREFLIGHT.md) is the attendee-facing page this
email points at.

Send it **three days out**, and send the reminder **the morning before**. Not
the night before: someone will need a package their IT department has to
approve, and that takes a working day.

---

## The email

> **Subject: Before Thursday's agent workshop — 30 minutes today, please**
>
> We build and deploy a real AI agent to your own Google Cloud project in sixty
> minutes. That only fits because the setup happens beforehand, so please do
> this today rather than on the morning.
>
> It takes about 30 minutes, most of it waiting on downloads. You need a laptop
> you can install software on, a Google account, and a card for Google's free
> trial. The whole workshop costs about 20 cents of it.
>
> Start here:
>
> ```
> git clone https://github.com/pedrodcsjostrom/adk-invoice-workshop.git
> cd adk-invoice-workshop
> open docs/PREFLIGHT.md
> ```
>
> Or read the same page in the browser:
> https://github.com/pedrodcsjostrom/adk-invoice-workshop/blob/main/docs/PREFLIGHT.md
>
> The last step runs one script that checks everything:
>
> ```
> ./scripts/preflight_check.sh
> ```
>
> **Reply with the report block it prints, whatever it says.** If it says NOT
> READY, send it anyway — that is exactly what I need to see, and there is time
> to fix it. If you cannot get there at all, come anyway: there is a shared
> sandbox you can use, and you will not be left behind.
>
> — Peter

## The reminder, the morning before

> Quick reminder: if you have not sent me your pre-flight report yet, please run
> it today. It takes 30 minutes and the workshop is hands-on from minute five.
> Everything is here:
> https://github.com/pedrodcsjostrom/adk-invoice-workshop/blob/main/docs/PREFLIGHT.md

## Reading forty reports

Every report has one `RESULT` line, and it is the only line you have to read
first. Sort the replies into three piles.

**READY** — nothing to do. `model ... reachable=true` is the line that means it
genuinely works rather than looks configured.

**NOT READY, fix yourself** — reply with the one command from their own report.
Do not diagnose it further; the script already did. The usual four:

| What it says | What you say |
|---|---|
| `cloud-run-proxy is missing` | The apt or tarball line from their report. This is the one that fails silently at 0:41 if it is not fixed. |
| `N API(s) not enabled` | The `gcloud services enable` line from their report, then wait ten minutes and re-run. |
| `no application default credentials` / `no quota project` | The two commands, in that order. The order is the whole fix. |
| `dependencies are not installed` / `terraform init` | `uv sync`, `terraform -chdir=infra init`. Stress that doing it on the venue wifi will not work. |

**NOT READY, needs an admin** — a corporate organization. These are the ones to
handle personally, today, because they cannot fix themselves. Ask whether they
can use a personal Google account instead. If not, put them on the sandbox and
tell them so in advance, so it is a plan rather than a surprise.

## Who has not replied

Anyone silent by the morning is a sandbox attendee until proven otherwise. Count
them, because that number decides how many sandbox handouts you print.

## What the reports tell you about the room

Keep them. The distribution of failures is the best data you will get for
running this again, and the version line at the top of each report ties a
failure to an exact commit of the kit.
