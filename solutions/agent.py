"""The invoice analyzer: one agent, three tools.

The whole point of the workshop is the re-read below. The agent reads the
invoice, a tool tells it the numbers do not agree, and it goes back to the
document rather than to its own imagination.

The instruction is assembled from three blocks because the middle one — the
re-read, steps 3 and 4 — is fill-in two: attendees type it themselves, after
the room has watched a run without it.
"""

import os

from google.adk.agents import LlmAgent

from invoice_agent.models import InvoiceRecord
from invoice_agent.tools import (
    check_invoice_arithmetic,
    lookup_supplier,
    save_invoice_record,
)

# Terraform passes INVOICE_MODEL to the Cloud Run service, so the deployed
# agent and the laptop one are one edit apart, not two.
MODEL = os.environ.get("INVOICE_MODEL", "gemini-3.5-flash")

_STEPS_READ_AND_CHECK = """\
You process supplier invoices. The user gives you one invoice document.

Work through these steps in order.

1. Read the document. Take every field and every charge line off it.

2. Call check_invoice_arithmetic with the line items and the total exactly as
   you read them. Never skip this, even when the numbers look obviously right.

"""

# ===== FILL-IN 2 of 2 — invoice_agent/agent.py — steps 3 and 4 of INSTRUCTION =
#
# Steps 1, 2 and 5-8 are written for you. Steps 3 and 4 are yours, and they are
# the whole workshop: when the arithmetic check comes back ok=false, send the
# agent back to the document, then make it check a second time.
#
# Prose, not code. Write it in your own words — this is what puts "the agent
# went back to the document" on screen.
#
# Behind, or want the version this was tuned to? One command:
#     cp solutions/agent.py invoice_agent/agent.py

_STEPS_RE_READ = """\
3. If the check reports ok=false, do not accept your reading yet. Go back to
   the document and read it a second time, looking for what the first pass
   could have got wrong. In order of likelihood: a charge line you did not
   include, often a deposit, delivery, surcharge or adjustment printed below
   the table rule, in the terms, or on a later page; a credit that should be
   negative, printed as a positive number with CR beside it; a quantity or
   unit price read off the wrong row.

4. Call check_invoice_arithmetic a second time with the reading you now
   believe. Do this even when the second look changed nothing — the second
   check is what records the outcome of going back.

"""

# ===== END FILL-IN 2 ==========================================================

_STEPS_SAVE_AND_ANSWER = """\
5. If the second check also reports ok=false, the invoice itself does not add
   up and no amount of re-reading will fix it. Keep every number exactly as
   printed, discrepancy included, and carry on to step 6. Do not check a third
   time.

6. Call lookup_supplier once with the supplier name printed on the document.
   Use the supplier_id it returns, or null when found is false.

7. Call save_invoice_record once with your finished record. An invoice that
   does not add up is still saved; the store flags it.

8. Return that same record as your answer.

Two rules that override everything above.

Never invent or adjust a number to make the arithmetic work. Change a number
only when you can see on the document that your earlier reading was wrong.

Never drop a line, and never add a line that is not printed, to close a gap.
"""

INSTRUCTION = _STEPS_READ_AND_CHECK + _STEPS_RE_READ + _STEPS_SAVE_AND_ANSWER

root_agent = LlmAgent(
    name="invoice_analyzer",
    model=MODEL,
    description="Reads an invoice document, checks it adds up, and files it.",
    instruction=INSTRUCTION,
    tools=[check_invoice_arithmetic, lookup_supplier, save_invoice_record],
    output_schema=InvoiceRecord,
)
