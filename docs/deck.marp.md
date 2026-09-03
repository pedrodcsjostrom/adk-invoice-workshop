---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 30px; padding: 60px 70px; }
  section.lead { text-align: center; }
  h1 { font-size: 54px; line-height: 1.15; }
  h2 { font-size: 40px; }
  code { font-size: 0.85em; }
  footer { font-size: 15px; opacity: 0.55; font-family: monospace; }
  .big { font-size: 46px; font-weight: 600; line-height: 1.5; }
  .url { font-size: 44px; font-family: monospace; }
---

<!-- _class: lead -->

# Build an agent that reads an invoice, catches one that does not add up, and files it anyway with a flag.

## 60 minutes. On your own Google Cloud project.

<span class="url">bit.ly/adk-invoices</span>

`[ QR code ]`

---

# Pre-flight did not pass? Use the sandbox.

**Project:** `adk-sandbox-________`  ·  **Service:** `invoice-agent`  ·  **Region:** `europe-west1`

```
gcloud auth login
gcloud run services proxy invoice-agent \
  --region europe-west1 --project adk-sandbox-________
```

Then open `http://localhost:8080`.

No credentials, no keys. Sign in with the Google account you already have.

<!-- Proxy missing? sudo apt-get install google-cloud-cli-cloud-run-proxy -->

---

<!-- _footer: 'cp solutions/tools.py invoice_agent/tools.py   ·   cp solutions/agent.py invoice_agent/agent.py' -->

# You will type two things today.

**1 · `check_invoice_arithmetic`** — a tool, ~15 lines.
*The docstring is prompt text.*

**2 · Steps 3 and 4 of `INSTRUCTION`** — twelve lines of English.
*You are writing policy, not code.*

Both are marked in the file. Both have a solution next to them.

```
uv run pytest tests/test_gap_arithmetic.py
```

### It is red. That is correct.

---

<!-- _class: lead -->
<!-- _footer: 'cp solutions/tools.py invoice_agent/tools.py   ·   cp solutions/agent.py invoice_agent/agent.py' -->

# An agent is three things.

<span class="big">A model. &nbsp; Some tools. &nbsp; An instruction.</span>

Run in a loop until it stops asking for tools.

### There is no fourth thing.

---

<!-- _footer: 'cp solutions/tools.py invoice_agent/tools.py   ·   cp solutions/agent.py invoice_agent/agent.py' -->

# Three things to take away.

**1 · A tool's description is its interface.**
English is the type signature.

**2 · The interesting behaviour is in the loop, not the model.**
Nothing clever happened in any single call.

**3 · An agent you cannot watch is an agent you cannot trust.**
The trace was the product.

---

<!-- _class: lead -->

<span class="url">bit.ly/adk-invoices</span>

`[ QR code ]`

The take-home is in the README.

**Feedback:** `[ TBD — link or QR ]`
