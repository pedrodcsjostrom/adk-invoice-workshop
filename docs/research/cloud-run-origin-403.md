# The developer UI does not load through the proxy, and the one-line reason

Ticket [#52](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/52).
Revises the proxy conclusion in [#15](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/15).

Opening the deployed developer UI through `gcloud run services proxy` gives a
styled blank page. The document arrives, the stylesheet arrives, and every
JavaScript bundle is refused. The Angular app never starts.

## The symptom, in a real browser

Against the live service in `my-invoice-workshop-0`, with the proxy on
`127.0.0.1:8088`:

| Route | curl | Chrome |
| --- | --- | --- |
| `/dev-ui/` | 200 | blank page, dark background, correct title |
| `/records` | 200 | renders, rows and all |

That gap is the whole finding, and it is why #15 missed it. #15 checked status
codes and read three 200s. A browser sends requests curl does not.

## The cause

Cloud Run's front door refuses an authenticated request that carries an
`Origin` header the service did not issue. It answers in about half a second,
before the container sees anything:

```
HTTP/2 403
content-type: text/plain
server: Google Frontend

Forbidden: origin not allowed
```

Measured against `/dev-ui/` with a valid identity token on every row:

| Request | Status |
| --- | --- |
| No `Origin` | 200 |
| `Origin: http://127.0.0.1:8080` | 403 |
| `Origin: https://localhost:8080` | 403 |
| `Origin: null` | 403 |
| Empty `Origin` | 403 |
| `Origin:` the service's own `run.app` URL | 200 |
| Module-script fetch headers, no `Origin` | 200 |

It makes no difference whether the token rides in `Authorization` or in
`X-Serverless-Authorization`; both are 403 with an `Origin` and 200 without
one. This is a cross-origin rule, not an authentication one.

The developer UI is an Angular app whose bundles are `type="module"`. Module
scripts are fetched in CORS mode, so the browser attaches `Origin:
http://localhost:8080` even though the script sits on the same origin as the
document. The document navigation and the stylesheet are not fetched that way,
which is exactly why the page renders styled and empty.

**The proxy is not at fault.** #52 diagnosed this as the proxy declining to
attach the identity token to requests carrying an `Origin`. That is wrong, and
worth correcting because it changes what a fix would look like. Both
`cloud-run-proxy` binaries on this machine — the apt one at 0.5.1 and the
tarball one — were run against a local server that printed what it received:

```
GET /a  no Origin    X-Serverless-Authorization: Bearer <token>
GET /b  with Origin  X-Serverless-Authorization: Bearer <token>
GET /c  Origin + Sec-Fetch-Mode: cors, Sec-Fetch-Dest: script
                     X-Serverless-Authorization: Bearer <token>
```

The token is attached every time. The proxy simply passes `Origin` through, and
Cloud Run rejects it. So the fix is not a token-injecting proxy: it is a proxy
that **deletes one request header**. That is a much smaller thing than #52
assumed.

## Deleting the header, built and proved

`scripts/strip_origin_proxy.py` is that proxy, in forty lines. It listens on
8090, forwards to the `cloud-run-proxy` on 8080, and strips `Origin` from the
client-to-server byte stream. It rewrites bytes rather than parsing requests,
which is how it relays server-sent events without understanding them.

Against the same live service, every route that was 403 with an `Origin`
returns 200 through the shim, including `/dev-ui/main-*.js`. In Chrome the
developer UI loads fully with `invoice_agent` already selected. The rigged
Halden PDF was uploaded through the chat box and produced the whole trace in
the events pane:

```
check_invoice_arithmetic -> check_invoice_arithmetic
  -> lookup_supplier -> save_invoice_record
```

A separate `/run_sse` call carrying an `Origin` streamed nine events in 18s, so
streaming survives the shim. The record reached Firestore either way.

**It is still a second process in the hot path at 0:41**, which is why the run
of show does not use it. It is an escape hatch and a debugging tool, not the
demo. The earlier claim here that the UI could not be reached "by any route the
kit is willing to take" was too strong.

This is environment-independent: not a cold start, not project IAM, not the
attendee's credentials.

## What replaces the UI at 0:42

`scripts/probe_deployed.py` already drives the deployed agent over the same
HTTP API the developer UI uses, and it sends no `Origin`. Run against the live
service through the proxy:

```
tool calls: check_invoice_arithmetic -> check_invoice_arithmetic
            -> lookup_supplier -> save_invoice_record
elapsed: 17.2s
```

Two checks with the re-read between them, running as the stack's service
account. The record reached the named Firestore database and the original PDF
reached the bucket. The records page then rendered both runs at
`localhost:8088/records` in Chrome — supplier resolved to `SUP-0004`, total
12,671.00 NOK, **adds up: no**, source a `gs://` URI.

So the deployed agent still runs in front of the room, still fails the
arithmetic twice, and still files the flagged record. The only thing lost is
the browser it used to run in — and a terminal printing the tool trace is a
better projector surface for that than a chat window anyway.

## What this does not change

The proxy stays. It is how `/records` is reached, there is still no public URL
in the kit, and the `cloud-run-proxy` pre-flight check is as load-bearing as it
was. Allowing unauthenticated invocations remains rejected for the reasons at
the top of `infra/service.tf`.

---

## Closing note, 2026-09-06: what was built

Everything above is what was measured in early September, and it stands. What
it led to is [#55](https://github.com/pedrodcsjostrom/adk-invoice-workshop/issues/55),
which landed as six tickets, and the short version is that the problem this
document diagnoses no longer has to be worked around at all.

- **The header rule was re-measured on the upload path** and it is worse than
  the table above shows, because the table is all GETs. A POST with no `Origin`
  reaches the container; the same POST with `Origin: http://localhost:8080` is
  refused. A browser attaches `Origin` to every request that is not a plain page
  load, including a same-origin form post, so this was never only a developer UI
  problem — any page we served from Cloud Run would render and then fail on its
  first upload.
- **The developer UI is no longer deployed.** The deployed service is a plain
  FastAPI application of ours serving an upload page at `/` and the records page
  at `/records` (ADR-0001, ADR-0002). So the symptom this document opens with —
  a styled blank page at `/dev-ui/` — is now a fact about something the container
  does not serve. The developer UI is the local tool, under `adk web`, and the
  hour's trace is still read there.
- **The Origin shim became the way in, not the escape hatch.** It is
  `scripts/origin_shim.py`, renamed from `strip_origin_proxy.py`, and it is one
  command rather than two processes on two ports: it starts
  `gcloud run services proxy` as a child on a port of its own, listens on 8080,
  deletes `Origin`, prints one URL, and takes the child down on Ctrl-C. The
  40-line byte-rewriting core is the same code that was proved above. ADR-0004
  records the decision; #61 is the ticket. The 8090 in the section above is
  history — there is no second port any more.
- **`scripts/probe_deployed.py` is no longer the deployed route, and no longer
  speaks ADK's REST API.** It was repointed at `POST /analyze`, the same
  multipart request the upload page sends, because the deployed application
  does not mount ADK's HTTP surface any more. "What replaces the UI at 0:42"
  above is superseded: 0:42 is a browser upload against the attendee's own
  service, and the probe is a check of the deploy rather than a substitute for
  the room seeing it.

**So: do not re-diagnose this.** The 403 is real, it is a Cloud Run front-door
cross-origin rule, and the answer is in the repo. What is worth re-reading here
is the elimination — the proxy attaches the token either way, so the fix was
never a token-injecting proxy — because that is the part that cost the time.
