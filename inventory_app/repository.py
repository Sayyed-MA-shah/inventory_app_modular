from typing import List, Optional, Dict, Any
from datetime import datetime
from . import database

def add_color(name: str):
    with database.get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO colors(name) VALUES(?)", (name.strip(),))

def add_size(name: str):
    with database.get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO sizes(name) VALUES(?)", (name.strip(),))

def list_colors() -> List[str]:
    with database.get_connection() as conn:
        rows = conn.execute("SELECT name FROM colors ORDER BY name").fetchall()
    return [r[0] for r in rows]

def list_sizes() -> List[str]:
    with database.get_connection() as conn:
        rows = conn.execute("SELECT name FROM sizes ORDER BY name").fetchall()
    return [r[0] for r in rows]

def get_color_id(name: str) -> Optional[int]:
    with database.get_connection() as conn:
        row = conn.execute("SELECT id FROM colors WHERE name=?", (name,)).fetchone()
        return row["id"] if row else None

def get_size_id(name: str) -> Optional[int]:
    with database.get_connection() as conn:
        row = conn.execute("SELECT id FROM sizes WHERE name=?", (name,)).fetchone()
        return row["id"] if row else None

def add_product(name: str, rack: str) -> int:
    with database.get_connection() as conn:
        cur = conn.execute("INSERT INTO products(name, rack_number) VALUES(?,?)", (name.strip(), rack.strip()))
        return cur.lastrowid

def get_or_create_product(name: str, rack: str) -> int:
    with database.get_connection() as conn:
        row = conn.execute("SELECT id FROM products WHERE name=? AND rack_number=?", (name.strip(), rack.strip())).fetchone()
        if row:
            return row["id"]
        cur = conn.execute("INSERT INTO products(name, rack_number) VALUES(?,?)", (name.strip(), rack.strip()))
        return cur.lastrowid

def add_variant(product_id: int, color_id: int, size_id: int, qty: int, retail: float, wholesale: float) -> int:
    with database.get_connection() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO product_variants(product_id, color_id, size_id, quantity, retail_price, wholesale_price)
                 VALUES(?,?,?,?,?,?)""",
            (product_id, color_id, size_id, qty, retail, wholesale)
        )
        if cur.rowcount == 0:
            conn.execute(
                """UPDATE product_variants
                       SET quantity = quantity + ?,
                           retail_price = ?,
                           wholesale_price = ?
                     WHERE product_id=? AND color_id=? AND size_id=?""",
                (qty, retail, wholesale, product_id, color_id, size_id)
            )
            row = conn.execute(
                "SELECT id FROM product_variants WHERE product_id=? AND color_id=? AND size_id=?",
                (product_id, color_id, size_id)
            ).fetchone()
            return row["id"]
        return cur.lastrowid
# _____________________________
# ...existing code...
def add_customer(customer: dict) -> int:
    """
    Insert a customer record. Expects dict with keys: name, phone, address, type.
    Returns inserted customer's id.
    """
    name = (customer.get("name") if isinstance(customer, dict) else str(customer)).strip()
    phone = (customer.get("phone") if isinstance(customer, dict) else "") or ""
    address = (customer.get("address") if isinstance(customer, dict) else "") or ""
    ctype = (customer.get("type") if isinstance(customer, dict) else "retail") or "retail"
    created_at = datetime.now().isoformat(timespec="seconds")
    with database.get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO customers(name, phone, address, type, created_at) VALUES(?,?,?,?,?)",
            (name, phone, address, ctype, created_at)
        )
        return cur.lastrowid

def get_customer_by_name_or_id(q: str) -> list:
    """
    Return list of customer dicts matching name LIKE q or id == q (if numeric).
    """
    q = (q or "").strip()
    if not q:
        return []
    with database.get_connection() as conn:
        if q.isdigit():
            rows = conn.execute("SELECT id, name, phone, address, type FROM customers WHERE id = ?", (int(q),)).fetchall()
        else:
            rows = conn.execute("SELECT id, name, phone, address, type FROM customers WHERE name LIKE ? ORDER BY name", (f"%{q}%",)).fetchall()
    return [dict(r) for r in rows]

def search_products(q: str) -> list:
    """
    Search product_variants (joined with products/sizes/colors) and return list of dicts:
    {id: variant_id, name, size, color, retail_price, wholesale_price, rack, quantity}
    """
    q = (q or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    sql = """
        SELECT v.id as id, p.name as name, s.name as size, c.name as color,
               v.retail_price as retail_price, v.wholesale_price as wholesale_price,
               p.rack_number as rack, v.quantity as quantity
          FROM product_variants v
          JOIN products p ON p.id = v.product_id
          JOIN sizes s ON s.id = v.size_id
          JOIN colors c ON c.id = v.color_id
         WHERE p.name LIKE ? OR p.rack_number LIKE ? OR s.name LIKE ? OR c.name LIKE ?
         ORDER BY p.name, s.name, c.name
    """
    with database.get_connection() as conn:
        rows = conn.execute(sql, (like, like, like, like)).fetchall()
    return [dict(r) for r in rows]

def get_product_price(variant_id: int, pricing_type: str = "retail") -> float:
    """
    Return unit price for a variant id according to pricing_type ('retail'|'wholesale').
    """
    with database.get_connection() as conn:
        row = conn.execute("SELECT retail_price, wholesale_price FROM product_variants WHERE id = ?", (int(variant_id),)).fetchone()
        if not row:
            return 0.0
        return float(row["retail_price"] if pricing_type == "retail" else row["wholesale_price"])

def get_branding() -> dict:
    """
    Read optional config.json next to package root and return dict (used by UI).
    """
    import os, json
    cfg_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "config.json"))
    try:
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if isinstance(cfg, dict):
                    return cfg
    except Exception:
        pass
    return
# ____________________________

def list_variants(filters: Dict[str, Any]) -> list:
    sql = """
        SELECT p.name as product, p.rack_number as rack,
               s.name as size, c.name as color,
               v.quantity as qty, v.retail_price as retail, v.wholesale_price as wholesale,
               v.id as vid
          FROM product_variants v
          JOIN products p ON p.id = v.product_id
          JOIN sizes s ON s.id = v.size_id
          JOIN colors c ON c.id = v.color_id
         WHERE 1=1
    """
    params = []
    if filters.get("product"):
        sql += " AND p.name LIKE ?"
        params.append(f"%{filters['product'].strip()}%")
    if filters.get("rack"):
        sql += " AND p.rack_number LIKE ?"
        params.append(f"%{filters['rack'].strip()}%")
    if filters.get("size"):
        sql += " AND s.name = ?"
        params.append(filters["size"])
    if filters.get("color"):
        sql += " AND c.name = ?"
        params.append(filters["color"])
    status = filters.get("status")
    if status == "Low Stock":
        sql += " AND v.quantity BETWEEN 1 AND ?"
        params.append(int(filters.get("low_threshold", 5)))
    elif status == "Out of Stock":
        sql += " AND v.quantity = 0"

    sql += " ORDER BY p.name, rack, size, color"
    with database.get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [tuple(r) for r in rows]

def restock_units(variant_id: int, units: int):
    with database.get_connection() as conn:
        conn.execute("UPDATE product_variants SET quantity = quantity + ? WHERE id=?", (units, variant_id))

def restock_boxes(variant_id: int, per_box: int, boxes: int):
    restock_units(variant_id, per_box * boxes)

def update_prices(variant_id: int, retail: float, wholesale: float):
    with database.get_connection() as conn:
        conn.execute("UPDATE product_variants SET retail_price=?, wholesale_price=? WHERE id=?", (retail, wholesale, variant_id))

def delete_variant(variant_id: int):
    with database.get_connection() as conn:
        conn.execute("DELETE FROM product_variants WHERE id=?", (variant_id,))

def get_variant(variant_id: int):
    with database.get_connection() as conn:
        return conn.execute(
            """SELECT v.*, p.name as product_name, p.rack_number as rack, s.name as size, c.name as color
                   FROM product_variants v
                   JOIN products p ON p.id=v.product_id
                   JOIN sizes s ON s.id=v.size_id
                   JOIN colors c ON c.id=v.color_id
                  WHERE v.id=?""",
            (variant_id,)
        ).fetchone()

def get_product_id_from_variant(variant_id: int) -> Optional[int]:
    with database.get_connection() as conn:
        row = conn.execute("SELECT product_id FROM product_variants WHERE id=?", (variant_id,)).fetchone()
        return row["product_id"] if row else None

def delete_product(product_id: int):
    with database.get_connection() as conn:
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))

def list_products() -> list:
    with database.get_connection() as conn:
        return conn.execute("SELECT id, name, rack_number FROM products ORDER BY name").fetchall()

def create_invoice(customer_name: str, customer_phone: str, pricing_type: str, tax_rate: float, items: list) -> int:
    from datetime import datetime
    created_at = datetime.now().isoformat(timespec="seconds")
    with database.get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO invoices(customer_name, customer_phone, pricing_type, tax_rate, created_at)
                 VALUES(?,?,?,?,?)""",
            (customer_name.strip(), customer_phone.strip(), pricing_type, float(tax_rate), created_at)
        )
        invoice_id = cur.lastrowid

        for it in items:
            vid = int(it["variant_id"])
            qty = int(it["quantity"])
            vr = conn.execute("SELECT retail_price, wholesale_price, quantity FROM product_variants WHERE id=?", (vid,)).fetchone()
            if not vr:
                raise ValueError(f"Variant {vid} not found")
            unit = vr["retail_price"] if pricing_type == "retail" else vr["wholesale_price"]
            if qty > vr["quantity"]:
                raise ValueError(f"Not enough stock for variant id {vid}")
            line_total = unit * qty
            conn.execute(
                """INSERT INTO invoice_items(invoice_id, variant_id, quantity, unit_price, line_total)
                     VALUES(?,?,?,?,?)""",
                (invoice_id, vid, qty, unit, line_total)
            )
            conn.execute("UPDATE product_variants SET quantity = quantity - ? WHERE id=?", (qty, vid))
    return invoice_id

def get_invoice(invoice_id: int):
    with database.get_connection() as conn:
        inv = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        items = conn.execute(
            """SELECT ii.*, p.name as product, s.name as size, c.name as color, pr.rack_number as rack
                   FROM invoice_items ii
                   JOIN product_variants v ON v.id=ii.variant_id
                   JOIN products pr ON pr.id=v.product_id
                   JOIN sizes s ON s.id=v.size_id
                   JOIN colors c ON c.id=v.color_id
                   JOIN products p ON p.id=v.product_id
                  WHERE ii.invoice_id=?""",
            (invoice_id,)
        ).fetchall()
    return inv, items
