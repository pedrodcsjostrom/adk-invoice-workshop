"""The invoice record — one definition, shared by the agent and every tool.

Declared once here so the agent's `output_schema`, the arithmetic check and the
persistence tool can never drift apart.
"""

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """One charge line on the invoice."""

    description: str = Field(description="What the line is for, as printed.")
    quantity: float = Field(description="Units billed.")
    unit_price: float = Field(description="Price per unit.")
    amount: float = Field(description="Line total as printed on the invoice.")


class InvoiceRecord(BaseModel):
    """The structured record extracted from one invoice."""

    supplier_name: str = Field(description="The supplier as printed on the invoice.")
    supplier_id: str | None = Field(
        default=None,
        description="Registry id from lookup_supplier, null when unresolved.",
    )
    invoice_number: str = Field(description="The invoice number.")
    invoice_date: str = Field(description="Invoice date in YYYY-MM-DD form.")
    currency: str = Field(description="Three-letter ISO 4217 currency code.")
    line_items: list[LineItem] = Field(description="Every charge line on the invoice.")
    total: float = Field(description="The total as printed on the invoice.")
