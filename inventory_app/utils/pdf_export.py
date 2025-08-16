from pathlib import Path

def export_invoice(invoice, items, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    fname_base = f"invoice_{invoice['id']}"
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm

        pdf_path = out_dir / f"{fname_base}.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        width, height = A4

        y = height - 30*mm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(20*mm, y, "INVOICE")
        y -= 8*mm

        c.setFont("Helvetica", 10)
        c.drawString(20*mm, y, f"Invoice ID: {invoice['id']}"); y -= 6*mm
        c.drawString(20*mm, y, f"Date: {invoice['created_at']}"); y -= 6*mm
        c.drawString(20*mm, y, f"Customer: {invoice['customer_name']}   Phone: {invoice['customer_phone']}"); y -= 6*mm
        c.drawString(20*mm, y, f"Pricing: {invoice['pricing_type'].title()}   Tax: {invoice['tax_rate']}%"); y -= 10*mm

        c.setFont("Helvetica-Bold", 10)
        c.drawString(20*mm, y, "Product")
        c.drawString(80*mm, y, "Size/Color")
        c.drawString(120*mm, y, "Qty")
        c.drawString(140*mm, y, "Unit")
        c.drawString(165*mm, y, "Line Total")
        y -= 5*mm
        c.line(20*mm, y, 190*mm, y)
        y -= 5*mm
        c.setFont("Helvetica", 10)

        subtotal = 0.0
        for it in items:
            if y < 30*mm:
                c.showPage()
                y = height - 30*mm
            unit = it["unit_price"]; line = it["line_total"]; subtotal += line
            c.drawString(20*mm, y, it["product"])
            c.drawString(80*mm, y, f"{it['size']} / {it['color']}")
            c.drawRightString(135*mm, y, str(it["quantity"]))
            c.drawRightString(160*mm, y, f"{unit:.2f}")
            c.drawRightString(190*mm, y, f"{line:.2f}")
            y -= 6*mm

        tax = subtotal * (float(invoice["tax_rate"]) / 100.0)
        total = subtotal + tax
        y -= 6*mm; c.line(120*mm, y, 190*mm, y); y -= 6*mm
        c.drawRightString(160*mm, y, "Subtotal:"); c.drawRightString(190*mm, y, f"{subtotal:.2f}"); y -= 6*mm
        c.drawRightString(160*mm, y, "Tax:"); c.drawRightString(190*mm, y, f"{tax:.2f}"); y -= 6*mm
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(160*mm, y, "TOTAL:"); c.drawRightString(190*mm, y, f"{total:.2f}")

        c.save()
        return pdf_path
    except Exception:
        html_path = out_dir / f"{fname_base}.html"
        subtotal = sum([it["line_total"] for it in items])
        tax = subtotal * (float(invoice["tax_rate"]) / 100.0)
        total = subtotal + tax
        rows = ""
        for it in items:
            rows += f"<tr><td>{it['product']}</td><td>{it['size']} / {it['color']}</td><td style='text-align:right'>{it['quantity']}</td><td style='text-align:right'>{it['unit_price']:.2f}</td><td style='text-align:right'>{it['line_total']:.2f}</td></tr>"
        html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Invoice {invoice['id']}</title>
<style>body{{font-family:Arial,sans-serif}} table{{width:100%;border-collapse:collapse}} th,td{{border:1px solid #ddd;padding:8px}} th{{background:#f5f5f5}}</style></head>
<body>
<h2>INVOICE</h2>
<p><b>Invoice ID:</b> {invoice['id']}<br>
<b>Date:</b> {invoice['created_at']}<br>
<b>Customer:</b> {invoice['customer_name']} &nbsp; <b>Phone:</b> {invoice['customer_phone']}<br>
<b>Pricing:</b> {invoice['pricing_type'].title()} &nbsp; <b>Tax:</b> {invoice['tax_rate']}%</p>
<table>
<thead><tr><th>Product</th><th>Size/Color</th><th>Qty</th><th>Unit</th><th>Line Total</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<h3 style="text-align:right">Subtotal: {subtotal:.2f}<br>Tax: {tax:.2f}<br>Total: {total:.2f}</h3>
</body></html>"""
        html_path.write_text(html, encoding="utf-8")
        return html_path
