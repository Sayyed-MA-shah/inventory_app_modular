import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "inventory.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS colors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sizes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rack_number TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            color_id INTEGER NOT NULL,
            size_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            retail_price REAL NOT NULL DEFAULT 0.0,
            wholesale_price REAL NOT NULL DEFAULT 0.0,
            UNIQUE(product_id, color_id, size_id),
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY(color_id) REFERENCES colors(id),
            FOREIGN KEY(size_id) REFERENCES sizes(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT,
            pricing_type TEXT CHECK(pricing_type IN ('retail','wholesale')) NOT NULL,
            tax_rate REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            variant_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
            FOREIGN KEY(variant_id) REFERENCES product_variants(id)
        )
    """)

    # Seed defaults for colors/sizes
    cur.execute("SELECT COUNT(*) FROM colors")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO colors(name) VALUES(?)", [("Red",),("Blue",),("Green",)])

    cur.execute("SELECT COUNT(*) FROM sizes")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO sizes(name) VALUES(?)", [("Small",),("Medium",),("Large",)])

    conn.commit()
    conn.close()
