"""Thinnest end-to-end slice: an invoice PDF in, structured JSON out.

One agent, one tool, one output schema — enough to prove the design the
workshop kit rests on actually runs against Vertex AI.
"""

from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent

MODEL = "gemini-3.5-flash"

# Stand-in for the real vendor registry. The slice only needs a tool call to
# happen at all, so the model can be seen using a tool and still returning
# schema-conforming JSON.
_VENDOR_REGISTRY = {
    "northwind supplies": "VEND-001",
    "acme office ltd": "VEND-002",
    "brightline logistics": "VEND-003",
}


def lookup_vendor(vendor_name: str) -> dict:
    """Look up a vendor in the company vendor registry.

    Call this once for the vendor named on the invoice, before returning the
    final record, so the invoice can be attached to a known vendor.

    Args:
        vendor_name: The vendor name exactly as printed on the invoice.
    """
    vendor_id = _VENDOR_REGISTRY.get(vendor_name.strip().lower())
    if vendor_id is None:
        return {"status": "not_found", "vendor_name": vendor_name}
    return {"status": "ok", "vendor_name": vendor_name, "vendor_id": vendor_id}


class LineItem(BaseModel):
    description: str = Field(description="What the line item is for.")
    quantity: float = Field(description="Units billed.")
    unit_price: float = Field(description="Price per unit.")
    amount: float = Field(description="Line total as printed on the invoice.")


class InvoiceRecord(BaseModel):
    """The structured record extracted from one invoice."""

    invoice_number: str = Field(description="The invoice number.")
    vendor_name: str = Field(description="The vendor as printed on the invoice.")
    vendor_id: str | None = Field(
        default=None,
        description="Registry id from the lookup_vendor tool, null if unknown.",
    )
    invoice_date: str = Field(description="Invoice date in YYYY-MM-DD form.")
    currency: str = Field(description="Three-letter currency code.")
    line_items: list[LineItem] = Field(description="Every line item on the invoice.")
    total: float = Field(description="The total as printed on the invoice.")


root_agent = LlmAgent(
    name="invoice_analyzer",
    model=MODEL,
    description="Reads an invoice document and returns a structured invoice record.",
    instruction=(
        "You read invoice documents. For the invoice the user gives you:\n"
        "1. Read every field and every line item off the document.\n"
        "2. Call lookup_vendor once with the vendor name printed on the invoice.\n"
        "3. Return the invoice record. Use the vendor_id the tool gave you, or"
        " null if the tool reported not_found.\n"
        "Report the totals as printed, even if they do not add up."
    ),
    tools=[lookup_vendor],
    output_schema=InvoiceRecord,
)
