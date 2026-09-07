# The pre-flight email, and how to read what comes back

Host-facing. [docs/PREFLIGHT.md](PREFLIGHT.md) is the attendee-facing page this
email points at.

Send it **three days out**, and send the reminder **the morning before**. Not
the night before: someone will need a package their IT department has to
approve, and that takes a working day.

---

## The email

The sendable text lives in
[emails/prep-email.es.txt](emails/prep-email.es.txt). It is Spanish, plain text,
and self-contained: every step an attendee types is in the body, and
[PREFLIGHT.md](PREFLIGHT.md) is linked only for the two long detours — the
tarball SDK, and corporate accounts. Paste it as plain text, not as HTML;
markdown syntax arrives as literal punctuation and attendees drag stray
backticks into their shells.

Three blanks to fill each delivery, listed in a comment at the top of the file:
the workshop date, the reply deadline, and the sign-off. Delete that comment
block before sending.

Edit the `.txt` rather than this page. This page is host operations; that file
is the artifact.

## The reminder, the morning before

Not a separate file — three sentences, sent only to whoever has not replied.

> Recordatorio rapido: si todavia no me has mandado tu informe de preparacion,
> ejecutalo hoy. Son 30 minutos y en el taller se trabaja con las manos desde el
> minuto cinco. Todo esta en el correo del [FECHA DEL PRIMER CORREO], y la
> pagina completa aqui:
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
