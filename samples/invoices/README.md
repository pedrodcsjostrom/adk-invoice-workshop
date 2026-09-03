# Sample invoice corpus

Nine synthetic invoices for the workshop demo. Every supplier, address, tax id
and bank detail here is invented. No real supplier data appears in this
directory, and nothing here was copied from a third party.

Regenerate the whole set with:

```
uv run --with reportlab --with pillow samples/generate_corpus.py
```

`expected.json` is the ground truth for each file: the printed supplier name,
invoice number, date, currency, line count, the sum of the line amounts, the
stated total, and whether arithmetic validation should pass. Treat it as the
answer key when tuning the agent, not as anything the agent gets to see.

## What each file is for

| File | Exercises |
| --- | --- |
| `01-northwind-clean.pdf` | The happy path. Single page, four lines, SEK. Validation passes. |
| `02-brightline-clean.pdf` | Happy path in a second visual template, coloured header bar, EUR. |
| `03-cascade-clean.pdf` | Happy path in a serif template, USD, with fractional quantities like 18.5 TB-months. |
| `04-halden-rigged-total.pdf` | **The centrepiece.** Every line multiplies out correctly, but the stated total of NOK 12,671.00 is 1,400.00 above the 11,271.00 the lines sum to. |
| `05-vertex-missable-line.pdf` | Recoverable variant of the same failure. The pallet deposit line is printed below the table rule as small print, so a first pass tends to drop it and the total does not reconcile. Counting it makes GBP 2,750.00 come out exactly. |
| `06-meridian-multipage.pdf` | Three pages, 23 line items, header repeated as a short strip on pages 2 and 3, total printed only on the last page. |
| `07-tallgrass-scan.jpg` | An image rather than a PDF. Rendered then roughed up: warm paper, uneven lighting, 1.4 degrees of rotation, grain, soft focus and heavy JPEG loss. |
| `08-almendra-spanish.pdf` | Non-English layout. Spanish labels throughout, `FACTURA`, `CANT.`, `IMPORTE`, `Total a pagar`. |
| `09-unknown-supplier.pdf` | A supplier deliberately absent from the vendor registry. The lookup misses and the record saves with a null `supplier_id`. |
| `10-ridgeway-terms-charge.pdf` | A fourth charge of GBP 480.00 stated as a sentence in the terms rather than as a table row, and included in the total. |
| `11-kestrel-credit-line.pdf` | A credit row printed in accounting notation as `620.00 CR` rather than as a negative number. |

## The rigged invoices, and what tuning found

`04-halden-rigged-total.pdf` is the demo document. Its lines do not sum to the
stated total and no re-reading can make them agree, so it shows the agent
noticing a bad invoice and filing it flagged.

Files 05, 10 and 11 were each built to make the agent misread on a first pass
so that a second look could put it right. **None of them work.** Gemini 3.5
Flash extracted every one of them correctly, first time, on every run — the
small-print row, the charge buried in the terms, and the `CR` credit alike.
The count across the whole corpus was 33 correct extractions out of 33.

They are kept because they are realistic documents worth having, and because
they are the evidence for that finding. But do not build a demo beat on the
agent failing to read one of them. See
`docs/research/failure-then-retry-tuning.md`.

## Constraints the corpus respects

- **No tax rows.** The record schema has no `subtotal` or `tax` field, so a
  separate VAT or IVA row would fail arithmetic validation for a reason the
  demo does not want. Tax is folded into the unit prices, and the invoices say
  so in their footers.
- **Every line multiplies out.** `quantity * unit_price` equals `amount` to the
  cent on every line of every file, including the rigged one. The only
  designed discrepancy is at the total.
- **Supplier names differ from the registry strings.** Printed names carry
  legal suffixes such as `AB`, `GmbH` and `S.L.`; the registry matches them
  through its `aliases` list, which is what the lookup tool is there to do.
- **Currencies vary** across SEK, EUR, USD, NOK and GBP, so nothing quietly
  assumes one currency.
