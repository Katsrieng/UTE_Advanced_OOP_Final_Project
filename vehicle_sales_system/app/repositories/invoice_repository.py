"""Persistence operations for invoice records."""

from app.models.invoice import Invoice

from .base import EntityRepository


class InvoiceRepository(EntityRepository):
    model = Invoice
    table = "invoices"
    pk = "invoice_id"
    fields = dict(
        code="invoice_number",
        sale_id="sale_id",
        date="issue_date",
        total="total_amount",
    )

    def for_sale(self, sale_id):
        rows = self.select("t.sale_id=%s", (sale_id,))
        return rows[0] if rows else None
