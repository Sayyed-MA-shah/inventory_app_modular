# Inventory Management System (Tkinter + SQLite)

Modular desktop app to manage products, attributes (Color/Size), inventory, search/filter, and invoices with PDF/HTML export.

## Features
- Add **Colors** and **Sizes**
- Add **Products** and **Variants** (size+color) each with **quantity**, **retail**, **wholesale**
- **Restock** (units or by box)
- **Search & Filter** by product, rack, size, color; filter by **Low Stock** or **Out of Stock**
- **Create Invoices** (retail/wholesale pricing, customer details, tax %). Exports **PDF** if `reportlab` is installed; otherwise HTML.
- All data persists in **SQLite** (`inventory.db`)
- Robust selection handling (no crashes when no row is selected)

## How to Run
1. Extract the ZIP.
2. (Optional for PDF) `pip install reportlab`
3. Run:
   ```bash
   python run_app.py
   ```
   or
   ```bash
   python -m inventory_app.main
   ```
