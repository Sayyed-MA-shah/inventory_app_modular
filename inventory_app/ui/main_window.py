# ...existing code...
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

# try package imports first, fall back to script-style imports
try:
    from .. import repository as repo
    from .dialogs import AddColorDialog, AddSizeDialog, AddProductDialog, AddVariantDialog
    from .invoice_window import InvoiceWindow
except Exception:
    try:
        import repository as repo
        from ui.dialogs import AddColorDialog, AddSizeDialog, AddProductDialog, AddVariantDialog
        from ui.invoice_window import InvoiceWindow
    except Exception:
        repo = None
        AddColorDialog = AddSizeDialog = AddProductDialog = AddVariantDialog = InvoiceWindow = None

# Sample data
SAMPLE_VARIANTS = [
    {"variant_id": "v1", "product": "Red T-Shirt", "color": "Red", "size": "M", "rack": "A1", "stock": 50, "price": 12.5},
    {"variant_id": "v2", "product": "Blue Jeans", "color": "Blue", "size": "L", "rack": "B3", "stock": 3, "price": 35.0},
    {"variant_id": "v3", "product": "Black Hat", "color": "Black", "size": "One", "rack": "C2", "stock": 0, "price": 9.99},
    {"variant_id": "v4", "product": "Red T-Shirt", "color": "Red", "size": "L", "rack": "A1", "stock": 8, "price": 12.5},
    {"variant_id": "v5", "product": "Green Hoodie", "color": "Green", "size": "M", "rack": "D4", "stock": 2, "price": 48.0},
]
# ...existing code...

class CollapsibleSection(ttk.Frame):
    def __init__(self, parent, title, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.columnconfigure(0, weight=1)
        self._open = tk.BooleanVar(value=True)
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew")
        self._toggle_btn = ttk.Checkbutton(header, text=title, style="Toolbutton", variable=self._open, command=self._toggle)
        self._toggle_btn.pack(fill="x")
        self.body = ttk.Frame(self, padding=(6,6))
        self.body.grid(row=1, column=0, sticky="ew")

    def _toggle(self):
        if self._open.get():
            self.body.grid()
        else:
            self.body.grid_remove()

class InventoryUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory - Beta UI")
        self.geometry("1100x700")
        self.configure(bg="#f3f4f6")
        self.style = ttk.Style(self)
        self._setup_styles()
        self.data = SAMPLE_VARIANTS.copy()
        self.filtered = list(self.data)
        self._last_action = ""
        self._build_ui()
        # attempt to load real data if repo available
        self._reload_from_repo()
        self._refresh_tree()
        self._update_status_bar("Ready")

    def _setup_styles(self):
        # General
        try:
            self.style.theme_use('clam')
        except Exception:
            pass
        self.style.configure("Ribbon.TFrame", background="#ffffff")
        self.style.configure("Ribbon.TButton", relief="flat", background="#ffffff", padding=6)
        self.style.configure("Card.TFrame", background="#ffffff", relief="groove", borderwidth=1)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.style.configure("Status.TLabel", background="#e9eef4")
        self.style.map("Ribbon.TButton", background=[("active", "#eef2f7")])

    def _build_ui(self):
        # Top ribbon
        ribbon = ttk.Frame(self, style="Ribbon.TFrame", padding=6)
        ribbon.grid(row=0, column=0, columnspan=3, sticky="ew")
        ribbon.columnconfigure(0, weight=1)
        btn_frame = ttk.Frame(ribbon, style="Ribbon.TFrame")
        btn_frame.grid(row=0, column=0, sticky="w")
        # wire buttons to actual handlers
        ribbon_buttons = [
            ("➕  Add Product", self._add_product),
            ("🧩  Add Attributes", self._add_attributes),
            ("📦  Inventory", self._open_inventory),
            ("🧾  Invoices", self._open_invoices),
            ("📊  Reports", self._open_reports),
        ]
        for text, cmd in ribbon_buttons:
            b = ttk.Button(btn_frame, text=text, style="Ribbon.TButton", command=cmd)
            b.pack(side="left", padx=4)

        # Main layout frames
        left = ttk.Frame(self, width=250, padding=8)
        left.grid(row=1, column=0, sticky="nsw")
        center = ttk.Frame(self, padding=(8,8))
        center.grid(row=1, column=1, sticky="nsew")
        right = ttk.Frame(self, width=200, padding=8)
        right.grid(row=1, column=2, sticky="nse")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Left sidebar - Search & Filters
        search_card = ttk.Frame(left, style="Card.TFrame", padding=8)
        search_card.pack(fill="x", pady=(0,8))
        ttk.Label(search_card, text="Search", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.search_name = tk.StringVar()
        ttk.Entry(search_card, textvariable=self.search_name).pack(fill="x", pady=4)
        self.search_name.trace_add("write", lambda *a: self._apply_filters())

        filters_card = ttk.Frame(left, style="Card.TFrame", padding=8)
        filters_card.pack(fill="both", expand=True)
        ttk.Label(filters_card, text="Filters", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        # Collapsible sections
        cs_name = CollapsibleSection(filters_card, "Search by Fields")
        cs_name.pack(fill="x", pady=6)
        ttk.Label(cs_name.body, text="Rack:").grid(row=0, column=0, sticky="w")
        self.search_rack = tk.StringVar()
        ttk.Entry(cs_name.body, textvariable=self.search_rack).grid(row=0, column=1, sticky="ew")
        ttk.Label(cs_name.body, text="Color:").grid(row=1, column=0, sticky="w")
        self.search_color = tk.StringVar()
        ttk.Entry(cs_name.body, textvariable=self.search_color).grid(row=1, column=1, sticky="ew")
        ttk.Label(cs_name.body, text="Size:").grid(row=2, column=0, sticky="w")
        self.search_size = tk.StringVar()
        ttk.Entry(cs_name.body, textvariable=self.search_size).grid(row=2, column=1, sticky="ew")
        for v in (self.search_rack, self.search_color, self.search_size):
            v.trace_add("write", lambda *a: self._apply_filters())

        cs_stock = CollapsibleSection(filters_card, "Stock Status")
        cs_stock.pack(fill="x", pady=6)
        self.stock_filter = tk.StringVar(value="all")
        ttk.Radiobutton(cs_stock.body, text="All", variable=self.stock_filter, value="all", command=self._apply_filters).pack(anchor="w")
        ttk.Radiobutton(cs_stock.body, text="Low (<5)", variable=self.stock_filter, value="low", command=self._apply_filters).pack(anchor="w")
        ttk.Radiobutton(cs_stock.body, text="Out of Stock", variable=self.stock_filter, value="out", command=self._apply_filters).pack(anchor="w")

        # Center - Treeview
        tree_frame = ttk.Frame(center)
        tree_frame.pack(fill="both", expand=True)
        columns = ("product", "color", "size", "rack", "stock", "price", "variant_id")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col, hd in zip(columns, ("Product", "Color", "Size", "Rack", "Stock", "Price", "variant_id")):
            self.tree.heading(col, text=hd)
            if col == "variant_id":
                self.tree.column(col, width=0, stretch=False, minwidth=0)
            elif col == "product":
                self.tree.column(col, width=220)
            else:
                self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.tag_configure('odd', background='#ffffff')
        self.tree.tag_configure('even', background='#f7fafc')

        # Context menu
        self.ctx_menu = tk.Menu(self, tearoff=0)
        self.ctx_menu.add_command(label="Restock", command=self._ctx_restock)
        self.ctx_menu.add_command(label="Update Price", command=self._ctx_update_price)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="Delete Variant", command=self._ctx_delete_variant)

        # Right sidebar - Actions
        actions_card = ttk.Frame(right, style="Card.TFrame", padding=8)
        actions_card.pack(fill="x")
        ttk.Label(actions_card, text="Actions", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0,6))
        act_buttons = [
            ("➕  Add Variant", self._add_variant),
            ("🔄  Restock", self._restock_prompt),
            ("💲  Update Price", self._update_price_prompt),
            ("🗑️  Delete Variant", self._delete_prompt)
        ]
        for text, cmd in act_buttons:
            b = ttk.Button(actions_card, text=text, command=cmd)
            b.pack(fill="x", pady=6)

        # Bottom status bar
        status = ttk.Frame(self, style="Status.TLabel")
        status.grid(row=2, column=0, columnspan=3, sticky="ew")
        self.status_label = ttk.Label(status, text="", style="Status.TLabel", padding=6)
        self.status_label.pack(side="left")

    # attempt to load data from repo; return True if loaded
    def _reload_from_repo(self):
        if not repo or not hasattr(repo, "list_variants"):
            return False
        try:
            rows = repo.list_variants({})
            if not rows:
                return False
            new = []
            first = rows[0]
            if isinstance(first, dict):
                for r in rows:
                    new.append({
                        "variant_id": str(r.get("variant_id") or r.get("vid") or r.get("id")),
                        "product": r.get("product") or r.get("name") or "",
                        "color": r.get("color") or "",
                        "size": r.get("size") or "",
                        "rack": r.get("rack") or "",
                        "stock": int(r.get("qty") or r.get("stock") or 0),
                        "price": float(r.get("price") or r.get("retail_price") or 0.0)
                    })
            else:
                for r in rows:
                    try:
                        prod = r[0]; rack = r[1]; size = r[2]; color = r[3]; qty = int(r[4]); price = float(r[5])
                        vid = str(r[7]) if len(r) > 7 else str(r[-1])
                    except Exception:
                        continue
                    new.append({"variant_id": vid, "product": prod, "color": color, "size": size, "rack": rack, "stock": qty, "price": price})
            if new:
                self.data = new
                self.filtered = list(self.data)
                return True
        except Exception:
            return False
        return False

    # -- Data & UI operations
    def _refresh_tree(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for idx, item in enumerate(self.filtered):
            tag = 'even' if idx % 2 == 0 else 'odd'
            self.tree.insert("", "end", values=(item["product"], item["color"], item["size"], item["rack"], item["stock"], f'{item["price"]:.2f}', item["variant_id"]), tags=(tag,))
        self._update_summary()

    def _apply_filters(self):
        q_name = self.search_name.get().strip().lower()
        q_rack = self.search_rack.get().strip().lower()
        q_color = self.search_color.get().strip().lower()
        q_size = self.search_size.get().strip().lower()
        sf = self.stock_filter.get()
        def keep(v):
            if q_name and q_name not in v["product"].lower():
                return False
            if q_rack and q_rack not in v["rack"].lower():
                return False
            if q_color and q_color not in v["color"].lower():
                return False
            if q_size and q_size not in v["size"].lower():
                return False
            if sf == "low" and not (0 < v["stock"] < 5):
                return False
            if sf == "out" and v["stock"] != 0:
                return False
            return True
        self.filtered = [v for v in self.data if keep(v)]
        self._refresh_tree()

    def _get_selected_variant(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0])["values"]
        variant_id = vals[-1]
        for v in self.data:
            if v["variant_id"] == variant_id:
                return v
        return None

    def _on_right_click(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.ctx_menu.tk_popup(event.x_root, event.y_root)

    def _ctx_restock(self):
        v = self._get_selected_variant()
        if not v:
            return
        self._restock_variant(v)

    def _ctx_update_price(self):
        v = self._get_selected_variant()
        if not v:
            return
        self._update_price_variant(v)

    def _ctx_delete_variant(self):
        v = self._get_selected_variant()
        if not v:
            return
        self._delete_variant(v)

    # -- Actions used by buttons
    def _add_product(self):
        if AddProductDialog:
            try:
                AddProductDialog(self)
                self.after(200, lambda: (self._reload_from_repo() and self._apply_filters()))
                self._update_status_bar("Opened Add Product")
            except Exception as e:
                self._update_status_bar(f"AddProduct failed: {e}")
        else:
            self._update_status_bar("Add Product not available")

    def _add_attributes(self):
        if AddColorDialog and AddSizeDialog:
            top = tk.Toplevel(self)
            top.title("Add Attributes")
            top.transient(self)
            ttk.Label(top, text="Choose attribute to add:").pack(padx=12, pady=(12,6))
            btn_frame = ttk.Frame(top); btn_frame.pack(padx=12, pady=8)
            ttk.Button(btn_frame, text="Add Color", command=lambda: (AddColorDialog(self), top.destroy(), self.after(200, lambda: (self._reload_from_repo() and self._apply_filters())))).pack(side="left", padx=6)
            ttk.Button(btn_frame, text="Add Size", command=lambda: (AddSizeDialog(self), top.destroy(), self.after(200, lambda: (self._reload_from_repo() and self._apply_filters())))).pack(side="left", padx=6)
            self._update_status_bar("Opened Add Attributes")
        else:
            self._update_status_bar("Add Attributes not available")

    def _add_variant(self):
        name = simpledialog.askstring("Add Variant", "Product name:")
        if not name:
            return
        vid = f"v{len(self.data)+1}"
        new = {"variant_id": vid, "product": name, "color": "N/A", "size": "N/A", "rack": "Unknown", "stock": 0, "price": 0.0}
        self.data.append(new)
        self._apply_filters()
        self._update_status_bar(f"Added variant {name} ({vid})")

    def _restock_prompt(self):
        v = self._get_selected_variant()
        if not v:
            messagebox.showinfo("Restock", "Select a variant first.")
            return
        self._restock_variant(v)

    def _restock_variant(self, variant):
        amount = simpledialog.askinteger("Restock", f"Units to add to {variant['product']} ({variant['size']}):", minvalue=1)
        if amount:
            variant["stock"] += amount
            self._apply_filters()
            self._update_status_bar(f"Restocked {amount} units of {variant['product']} ({variant['size']})")

    def _update_price_prompt(self):
        v = self._get_selected_variant()
        if not v:
            messagebox.showinfo("Update Price", "Select a variant first.")
            return
        self._update_price_variant(v)

    def _update_price_variant(self, variant):
        price = simpledialog.askfloat("Update Price", f"New price for {variant['product']} ({variant['size']}):", minvalue=0.0)
        if price is not None:
            variant["price"] = price
            self._apply_filters()
            self._update_status_bar(f"Updated price of {variant['product']} ({variant['size']}) to ${price:.2f}")

    def _delete_prompt(self):
        v = self._get_selected_variant()
        if not v:
            messagebox.showinfo("Delete", "Select a variant first.")
            return
        self._delete_variant(v)

    def _delete_variant(self, variant):
        if messagebox.askyesno("Delete Variant", f"Delete {variant['product']} ({variant['size']})?"):
            self.data = [d for d in self.data if d["variant_id"] != variant["variant_id"]]
            self._apply_filters()
            self._update_status_bar(f"Deleted variant {variant['product']} ({variant['size']})")

    # ribbon extra handlers
    def _open_inventory(self):
        # reload from repo if possible and refresh
        loaded = self._reload_from_repo()
        if loaded:
            self._apply_filters()
        self._update_status_bar("Opened Inventory")

    def _open_invoices(self):
        if InvoiceWindow:
            try:
                InvoiceWindow(self)
                self.after(300, lambda: (self._reload_from_repo() and self._apply_filters()))
                self._update_status_bar("Opened Invoices")
            except Exception as e:
                self._update_status_bar(f"Open invoices failed: {e}")
        else:
            self._update_status_bar("Invoices not available")

    def _open_reports(self):
        top = tk.Toplevel(self)
        top.title("Reports")
        top.transient(self)
        ttk.Label(top, text="Reports").pack(padx=12, pady=(12,6))
        ttk.Button(top, text="Low Stock (<=5)", command=lambda: (self._set_stock_filter_and_apply("low"), top.destroy())).pack(fill="x", padx=12, pady=6)
        ttk.Button(top, text="Out of Stock", command=lambda: (self._set_stock_filter_and_apply("out"), top.destroy())).pack(fill="x", padx=12, pady=6)
        ttk.Button(top, text="All", command=lambda: (self._set_stock_filter_and_apply("all"), top.destroy())).pack(fill="x", padx=12, pady=6)
        self._update_status_bar("Opened Reports")

    def _set_stock_filter_and_apply(self, mode):
        self.stock_filter.set(mode)
        self._apply_filters()
        self._update_status_bar(f"Report: {mode}")

    # -- UI helpers
    def _update_summary(self):
        total_products = len({d["product"] for d in self.data})
        variants = len(self.data)
        low_stock = sum(1 for d in self.data if 0 < d["stock"] < 5)
        out_stock = sum(1 for d in self.data if d["stock"] == 0)
        summary = f"Total Products: {total_products} | Variants: {variants} | Low Stock: {low_stock} | Out of Stock: {out_stock}"
        self._summary_text = summary
        self._compose_status()

    def _update_status_bar(self, last_action):
        self._last_action = last_action
        self._compose_status()

    def _compose_status(self):
        left = getattr(self, "_summary_text", "")
        right = getattr(self, "_last_action", "")
        self.status_label.config(text=f"{left}    Last action: {right}")

if __name__ == "__main__":
    app = InventoryUI()
    app.mainloop()
# ...existing code...