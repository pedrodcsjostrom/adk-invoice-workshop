# The developer UI cannot load through the proxy, and why

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
Cloud Run rejects it. So a hypothetical fix is not a token-injecting proxy: it
is a proxy that **deletes one request header**. That is a much smaller thing
than #52 assumed, and it is still a component in the hot path at 0:41 that
would have to relay the developer UI's server-sent events correctly. It is
written down here rather than built.

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
