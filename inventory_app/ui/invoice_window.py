# ...existing code...
"""
Rewritten invoice_window with:
 - Customer search + Add Customer option (uses dialogs.AddCustomerDialog)
 - Product search with dropdown (uses repository.search_products)
 - Pricing respects customer type via repository.get_product_price
 - Editable Qty & Unit Price in invoice table (double-click to edit)
 - Remove selected row button
 - Save exports to exports/ (reportlab if available; otherwise txt)
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    _HAS_RL = True
except Exception:
    _HAS_RL = False

# local modules
try:
    from .. import repository as repo
except Exception:
    try:
        import repository as repo
    except Exception:
        repo = None

try:
    from .dialogs import AddCustomerDialog
except Exception:
    # fallback simple dialog class if module import fails
    AddCustomerDialog = None

_DEFAULT_BRAND = {
    "business_name": "My Warehouse Ltd.",
    "address": "123 Main Street, City, Country",
    "phone": "1 (555) 123-456",
    "email": "sales@mywarehouse.com",
    "logo": os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")),
}

class InvoiceWindow(tk.Toplevel):
    def __init__(self, parent, invoice=None):
        super().__init__(parent)
        self.transient(parent)
        self.title("Invoice")
        self.geometry("1000x760")
        self.invoice = invoice or {}
        self.branding = self._load_branding()
        self.logo_img = None
        self._load_logo()

        # invoice state
        self.customer = {"id":"", "name":"", "phone":"", "address":"", "type":"retail"}
        self.items = []  # each: dict {pid, item, size, color, qty, unit}
        self.tax_percent = float(self.invoice.get("tax_percent", 10.0))

        # Build UI under defensive try/except was added before; keep normal build here
        self._build_ui()
        # preload invoice items if present
        for it in self.invoice.get("items", []):
            self._append_item(it)
        self._update_totals()

        self.tax_percent = float(self.invoice.get("tax_percent", 10.0))

        # ensure total-related TK vars exist before any UI actions that may call _update_totals
        self.subtotal_var = tk.StringVar("0.00")
        self.tax_var = tk.StringVar("0.00")
        self.grand_var = tk.StringVar("0.00")

        self._build_ui()

    def _branding_path(self):
        return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "config.json"))

    def _load_branding(self):
        try:
            if repo and hasattr(repo, "get_branding"):
                cfg = repo.get_branding()
                if isinstance(cfg, dict):
                    return {**_DEFAULT_BRAND, **cfg}
        except Exception:
            pass
        cfg_path = self._branding_path()
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if isinstance(cfg, dict):
                        return {**_DEFAULT_BRAND, **cfg}
        except Exception:
            pass
        return _DEFAULT_BRAND.copy()

    def _load_logo(self):
        path = self.branding.get("logo")
        if path and os.path.exists(path):
            try:
                if _HAS_PIL:
                    img = Image.open(path)
                    img.thumbnail((120,120), Image.LANCZOS)
                    self.logo_img = ImageTk.PhotoImage(img)
                else:
                    self.logo_img = tk.PhotoImage(file=path)
            except Exception:
                self.logo_img = None

    def _open_branding_dialog(self):
        import json, tkinter.filedialog as _fd
        d = tk.Toplevel(self); d.transient(self); d.title("Edit Branding")
        ttk.Label(d, text="Business Name").grid(row=0,column=0, sticky="e", padx=6, pady=6)
        e_name = ttk.Entry(d, width=60); e_name.grid(row=0,column=1, padx=6, pady=6); e_name.insert(0, self.branding.get("business_name",""))
        ttk.Label(d, text="Address (will be on PDF)").grid(row=1,column=0, sticky="e", padx=6, pady=6)
        e_addr = ttk.Entry(d, width=60); e_addr.grid(row=1,column=1, padx=6, pady=6); e_addr.insert(0, self.branding.get("address",""))
        ttk.Label(d, text="Phone").grid(row=2,column=0, sticky="e", padx=6, pady=6)
        e_phone = ttk.Entry(d, width=60); e_phone.grid(row=2,column=1, padx=6, pady=6); e_phone.insert(0, self.branding.get("phone",""))
        ttk.Label(d, text="Email").grid(row=3,column=0, sticky="e", padx=6, pady=6)
        e_email = ttk.Entry(d, width=60); e_email.grid(row=3,column=1, padx=6, pady=6); e_email.insert(0, self.branding.get("email",""))
        ttk.Label(d, text="Logo file").grid(row=4,column=0, sticky="e", padx=6, pady=6)
        e_logo = ttk.Entry(d, width=50); e_logo.grid(row=4,column=1, sticky="w", padx=6, pady=6); e_logo.insert(0, self.branding.get("logo",""))
        def pick_logo():
            p = _fd.askopenfilename(filetypes=[("PNG","*.png"),("JPEG","*.jpg;*.jpeg"),("All","*.*")])
            if p:
                e_logo.delete(0,tk.END); e_logo.insert(0,p)
        ttk.Button(d, text="Browse", command=pick_logo).grid(row=4,column=2,padx=6)
        def on_save_brand():
            cfg = {"business_name": e_name.get().strip(), "address": e_addr.get().strip(), "phone": e_phone.get().strip(), "email": e_email.get().strip(), "logo": e_logo.get().strip()}
            try:
                with open(self._branding_path(), "w", encoding="utf-8") as f:
                    json.dump({**_DEFAULT_BRAND, **cfg}, f, indent=2)
                messagebox.showinfo("Saved","Branding saved. Reopen invoice to refresh logo immediately.")
                d.destroy()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))
        ttk.Button(d, text="Save", command=on_save_brand).grid(row=5,column=1, sticky="e", padx=6, pady=8)

    def _build_ui(self):
        pad = 8
        header = ttk.Frame(self, padding=(pad,pad, pad,0))
        header.pack(fill="x")
        lf = ttk.Frame(header); lf.pack(side="left")
        if self.logo_img:
            ttk.Label(lf, image=self.logo_img).pack()
        else:
            ttk.Label(lf, text=self.branding.get("business_name"), font=("Helvetica",14,"bold")).pack()
        rf = ttk.Frame(header); rf.pack(side="right", expand=True, fill="x")
        ttk.Label(rf, text=self.branding.get("business_name"), font=("Helvetica",14,"bold")).pack(anchor="e")
        ttk.Button(rf, text="Edit Branding", command=self._open_branding_dialog).pack(anchor="e", pady=(6,0))

        # Top: invoice meta + customer
        top = ttk.Frame(self, padding=(pad,pad))
        top.pack(fill="x")
        meta = ttk.LabelFrame(top, text="Invoice", padding=6); meta.pack(side="right")
        self.invoice_no = tk.StringVar(value=self.invoice.get("invoice_no", f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"))
        self.date_var = tk.StringVar(value=self.invoice.get("date", datetime.now().strftime("%Y-%m-%d %H:%M")))
        ttk.Label(meta, text="Invoice #:").grid(row=0,column=0, sticky="w")
        ttk.Label(meta, textvariable=self.invoice_no).grid(row=0,column=1, sticky="e")
        ttk.Label(meta, text="Date:").grid(row=1,column=0, sticky="w")
        ttk.Label(meta, textvariable=self.date_var).grid(row=1,column=1, sticky="e")

        cust = ttk.LabelFrame(top, text="Billed To (address hidden in UI)", padding=6); cust.pack(side="left", fill="x", expand=True)
        ttk.Label(cust, text="Search Customer:").grid(row=0,column=0, sticky="w")
        self.cust_search_var = tk.StringVar()
        self.cust_search_e = ttk.Entry(cust, textvariable=self.cust_search_var, width=40)
        self.cust_search_e.grid(row=0,column=1, sticky="w", padx=(6,0))
        self.cust_search_e.bind("<KeyRelease>", self._on_cust_search_key)
        ttk.Button(cust, text="Add Customer", command=self._on_add_customer).grid(row=0,column=2, padx=6)

        # suggestions listbox for customers
        self.cust_suggestions = tk.Listbox(cust, height=5, width=60)
        self.cust_suggestions.grid(row=1,column=0, columnspan=3, pady=(6,4), sticky="w")
        self.cust_suggestions.bind("<<ListboxSelect>>", self._on_cust_suggestion_select)

        # product search
        search_frame = ttk.Frame(self, padding=(pad,0)); search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Search product:").pack(side="left")
        self.prod_search_var = tk.StringVar()
        self.prod_search_e = ttk.Entry(search_frame, textvariable=self.prod_search_var, width=60)
        self.prod_search_e.pack(side="left", padx=(6,4))
        self.prod_search_e.bind("<KeyRelease>", self._on_prod_search_key)
        ttk.Button(search_frame, text="Add selected", command=self._add_selected_product).pack(side="left", padx=6)

        # product suggestions listbox (shows name | size | color | price)
        self.prod_suggestions = tk.Listbox(self, height=8, width=120)
        self.prod_suggestions.pack(fill="x", padx=pad, pady=(4,8))
        self.prod_suggestions.bind("<Double-Button-1>", lambda e: self._add_selected_product())

        # invoice table
        tf = ttk.Frame(self); tf.pack(fill="both", expand=True, padx=pad)
        cols = ("item","size","color","qty","unit","total","pid")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", height=12)
        headers = [("Item",360), ("Size",80), ("Color",90), ("Qty",80), ("Unit Price",120), ("Total",120)]
        for col,(title,w) in zip(cols[:-1], headers):
            anchor = "e" if col in ("qty","unit","total") else "w"
            self.tree.heading(col, text=title)
            self.tree.column(col, width=w, anchor=anchor)
        self.tree.column("pid", width=0, stretch=False, minwidth=0)
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        sc = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview); sc.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sc.set)

        # bottom controls
        bottom = ttk.Frame(self, padding=(pad,6)); bottom.pack(fill="x")
        left_actions = ttk.Frame(bottom); left_actions.pack(side="left")
        ttk.Button(left_actions, text="Remove Selected", command=self._remove_selected).pack(side="left", padx=6)
        right_tot = ttk.Frame(bottom); right_tot.pack(side="right")
        self.subtotal_var = tk.StringVar("0.00"); self.tax_var = tk.StringVar("0.00"); self.grand_var = tk.StringVar("0.00")
        ttk.Label(right_tot, text="Subtotal:").grid(row=0,column=0, sticky="e")
        ttk.Label(right_tot, textvariable=self.subtotal_var, width=12, anchor="e").grid(row=0,column=1, padx=8)
        ttk.Label(right_tot, text="Tax %").grid(row=1,column=0, sticky="e")
        self.tax_spin = ttk.Spinbox(right_tot, from_=0, to=100, width=6, increment=0.5, command=self._on_tax_change)
        self.tax_spin.set(str(self.tax_percent)); self.tax_spin.grid(row=1,column=1, sticky="w")
        ttk.Label(right_tot, text="Tax Amt:").grid(row=2,column=0, sticky="e")
        ttk.Label(right_tot, textvariable=self.tax_var, width=12, anchor="e").grid(row=2,column=1, padx=8)
        ttk.Label(right_tot, text="Grand Total:", font=("Helvetica",11,"bold")).grid(row=3,column=0, sticky="e", pady=(6,0))
        ttk.Label(right_tot, textvariable=self.grand_var, font=("Helvetica",12,"bold"), width=12, anchor="e").grid(row=3,column=1, padx=8, pady=(6,0))

        actions = ttk.Frame(bottom); actions.pack(side="right", padx=(6,0))
        ttk.Button(actions, text="Save Invoice", command=self._save_invoice).pack(side="right", padx=6)
        ttk.Button(actions, text="Close", command=self.destroy).pack(side="right")

        # state holders for suggestions
        self._last_cust_results = []
        self._last_prod_results = []

    # --------- customer handlers ----------
    def _on_cust_search_key(self, _evt):
        q = (self.cust_search_var.get() or "").strip()
        self.cust_suggestions.delete(0, tk.END)
        self._last_cust_results = []
        if not q:
            return
        try:
            results = repo.get_customer_by_name_or_id(q) if repo and hasattr(repo, "get_customer_by_name_or_id") else []
        except Exception:
            results = []
        # if none found show "Add Customer" option
        if not results:
            self.cust_suggestions.insert(tk.END, f"Add new customer: \"{q}\"")
            self._last_cust_results.append({"action":"add","label":q})
            return
        for c in results:
            label = f"{c.get('name')}  —  {c.get('phone') or ''}  ({c.get('type') or 'retail'})"
            self.cust_suggestions.insert(tk.END, label)
            self._last_cust_results.append(c)

    def _on_cust_suggestion_select(self, _evt):
        sel = self.cust_suggestions.curselection()
        if not sel:
            return
        idx = sel[0]
        meta = self._last_cust_results[idx] if idx < len(self._last_cust_results) else None
        if meta is None:
            return
        if meta.get("action") == "add":
            # open add dialog
            self._on_add_customer(prefill_name=meta.get("label"))
            return
        # populate customer
        self.customer.update({
            "id": meta.get("id",""),
            "name": meta.get("name",""),
            "phone": meta.get("phone",""),
            "address": meta.get("address",""),
            "type": meta.get("type","retail")
        })
        # reflect selection in search entry
        self.cust_search_var.set(self.customer.get("name",""))
        self.cust_suggestions.delete(0, tk.END)

    def _on_add_customer(self, prefill_name=""):
        dlg = None
        if AddCustomerDialog:
            dlg = AddCustomerDialog(self)
            if prefill_name:
                try:
                    dlg.name_e.insert(0, prefill_name)
                except Exception:
                    pass
            self.wait_window(dlg)
            new = getattr(dlg, "result", None)
        else:
            name = simpledialog.askstring("Name","Customer name:", initialvalue=prefill_name, parent=self)
            if not name:
                return
            phone = simpledialog.askstring("Phone","Phone (optional):", parent=self)
            address = simpledialog.askstring("Address","Address (optional):", parent=self)
            ctype = simpledialog.askstring("Type","Type (retail/wholesale):", initialvalue="retail", parent=self)
            new = {"name": name, "phone": phone or "", "address": address or "", "type": (ctype or "retail")}
            # try persist
            if repo and hasattr(repo, "add_customer"):
                try:
                    new_id = repo.add_customer(new)
                    new["id"] = new_id
                except Exception:
                    pass
        if not new:
            return
        # persist if not already persisted
        if "id" not in new and repo and hasattr(repo, "add_customer"):
            try:
                new["id"] = repo.add_customer(new)
            except Exception:
                new["id"] = ""
        # set as selected customer
        self.customer.update({
            "id": new.get("id",""),
            "name": new.get("name",""),
            "phone": new.get("phone",""),
            "address": new.get("address",""),
            "type": new.get("type","retail")
        })
        self.cust_search_var.set(self.customer.get("name",""))
        self.cust_suggestions.delete(0, tk.END)

    # -------- product handlers ----------
    def _on_prod_search_key(self, _evt):
        q = (self.prod_search_var.get() or "").strip()
        self.prod_suggestions.delete(0, tk.END)
        self._last_prod_results = []
        if not q:
            return
        try:
            results = repo.search_products(q) if repo and hasattr(repo, "search_products") else []
        except Exception:
            results = []
        for p in results:
            # display price according to selected customer type
            ctype = self.customer.get("type","retail")
            price = p.get("retail_price",0.0)
            if repo and hasattr(repo, "get_product_price"):
                try:
                    price = repo.get_product_price(p.get("id"), ctype)
                except Exception:
                    price = price
            # show available qty and extra spacing for readability
            qty_avail = p.get("quantity", 0)
            label = f"{p.get('name')}   |   {p.get('size') or ''}   |   {p.get('color') or ''}   ${price:.2f}   [{qty_avail}]   [{p.get('id')}]"
            self.prod_suggestions.insert(tk.END, label)
            # store full meta including id and both prices
            self._last_prod_results.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "size": p.get("size"),
                "color": p.get("color"),
                "retail_price": float(p.get("retail_price") or 0.0),
                "wholesale_price": float(p.get("wholesale_price") or 0.0),
                "quantity": int(p.get("quantity") or 0),
            })
    def _add_selected_product(self):
        sel = self.prod_suggestions.curselection()
        if not sel:
            messagebox.showinfo("Select", "Please select a product from the list.")
            return
        idx = sel[0]
        meta = self._last_prod_results[idx]
        # determine unit price using customer type
        ctype = self.customer.get("type","retail")
        unit = meta.get("retail_price",0.0)
        if repo and hasattr(repo, "get_product_price"):
            try:
                unit = repo.get_product_price(meta.get("id"), ctype)
            except Exception:
                unit = unit
        # ask qty
        qty = simpledialog.askinteger("Quantity", "Enter quantity:", initialvalue=1, minvalue=1, parent=self)
        if qty is None:
            return
        self._append_item({
            "pid": meta.get("id"),
            "item": meta.get("name"),
            "size": meta.get("size"),
            "color": meta.get("color"),
            "qty": int(qty),
            "unit": float(unit)
        })
        # clear search
        self.prod_search_var.set("")
        self.prod_suggestions.delete(0, tk.END)

    # -------- tree / editing ----------
    def _append_item(self, it):
        # If same variant (pid) already in invoice, increase qty instead of adding duplicate row
        pid = it.get("pid")
        try:
            new_qty = int(it.get("qty", 1))
            new_unit = float(it.get("unit", 0.0))
        except Exception:
            new_qty = 1
            new_unit = 0.0
        for existing in self.items:
            if existing.get("pid") == pid and float(existing.get("unit", 0.0)) == float(new_unit):
                existing["qty"] = int(existing.get("qty", 0)) + new_qty
                self._refresh_tree_rows()
                self._update_totals()
                return
        # insert new row
        idx = len(self.items)
        tag = "even" if idx % 2 == 0 else "odd"
        total = new_qty * new_unit
        vals = (it.get("item",""), it.get("size",""), it.get("color",""), new_qty, f"{new_unit:.2f}", f"{total:.2f}", pid or "")
        self.tree.insert("", "end", values=vals, tags=(tag,))
        self.items.append({"pid": pid or "", "item": it.get("item",""), "size": it.get("size",""), "color": it.get("color",""), "qty": new_qty, "unit": new_unit})
        self._refresh_tree_rows()
        self._update_totals()

    def _refresh_tree_rows(self):
        for i, iid in enumerate(self.tree.get_children()):
            self.tree.item(iid, tags=("even",) if i%2==0 else ("odd",))
            try:
                it = self.items[i]
                total = int(it.get("qty",0)) * float(it.get("unit",0.0))
                vals = list(self.tree.item(iid, "values"))
                vals[3] = int(it.get("qty",0))
                vals[4] = f"{float(it.get('unit',0.0)):.2f}"
                vals[5] = f"{total:.2f}"
                self.tree.item(iid, values=vals)
            except Exception:
                pass

    def _on_tree_double_click(self, event):
        # identify column
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)  # e.g. '#4' for qty
        row = self.tree.identify_row(event.y)
        if not row:
            return
        idx = self.tree.index(row)
        if col in ("#4", "#5"):  # qty or unit
            cur = self.items[idx]
            if col == "#4":
                new_qty = simpledialog.askinteger("Edit Quantity", "Quantity:", initialvalue=cur.get("qty",1), minvalue=1, parent=self)
                if new_qty is None:
                    return
                cur["qty"] = int(new_qty)
            else:
                new_unit = simpledialog.askfloat("Edit Unit Price", "Unit price:", initialvalue=cur.get("unit",0.0), parent=self)
                if new_unit is None:
                    return
                cur["unit"] = float(new_unit)
            self._refresh_tree_rows()
            self._update_totals()

    # -------- totals / tax ----------
    def _on_tax_change(self):
        try:
            self.tax_percent = float(self.tax_spin.get())
        except Exception:
            self.tax_percent = 0.0
        self._update_totals()

    def _update_totals(self):
        subtotal = 0.0
        for it in self.items:
            try:
                subtotal += int(it.get("qty", 0)) * float(it.get("unit", 0.0))
            except Exception:
                pass
        tax_amt = subtotal * (self.tax_percent / 100.0)
        grand = subtotal + tax_amt
        self.subtotal_var.set(f"{subtotal:.2f}")
        self.tax_var.set(f"{tax_amt:.2f}")
        self.grand_var.set(f"{grand:.2f}")

    # -------- save/export (unchanged idea) ----------
    def _save_invoice(self):
        exports_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "exports"))
        os.makedirs(exports_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        fname = f"invoice_{self.invoice_no.get()}_{timestamp}"
        pdf_path = os.path.join(exports_dir, f"{fname}.pdf")
        txt_path = os.path.join(exports_dir, f"{fname}.txt")

        branding = self.branding
        customer = self.customer.copy()
        items = list(self.items)
        subtotal = float(self.subtotal_var.get()); tax_amt = float(self.tax_var.get()); grand = float(self.grand_var.get())

        if _HAS_RL:
            try:
                c = canvas.Canvas(pdf_path, pagesize=A4)
                w, h = A4
                margin = 20 * mm
                y = h - margin
                # logo / business on PDF
                logo = branding.get("logo")
                if logo and os.path.exists(logo):
                    try:
                        c.drawImage(logo, margin, y - 30*mm, width=40*mm, preserveAspectRatio=True, mask='auto')
                    except Exception:
                        c.setFont("Helvetica-Bold", 14); c.drawString(margin, y-10, branding.get("business_name"))
                else:
                    c.setFont("Helvetica-Bold", 14); c.drawString(margin, y-10, branding.get("business_name"))
                c.setFont("Helvetica", 9)
                bx = w - margin - 220; by = y - 6
                lines = [branding.get("business_name"), branding.get("address"), f"Phone: {branding.get('phone')}", f"Email: {branding.get('email')}"]
                for ln in lines:
                    c.drawRightString(w - margin, by, ln)
                    by -= 10
                # invoice meta
                meta_y = y - 40
                c.setFont("Helvetica-Bold", 10)
                c.drawString(margin, meta_y, f"Invoice #: {self.invoice_no.get()}")
                c.drawString(margin, meta_y - 12, f"Date: {self.date_var.get()}")
                # customer (include address)
                cy = meta_y
                c.setFont("Helvetica-Bold", 10); c.drawString(w - margin - 220, cy, "Billed To:")
                c.setFont("Helvetica", 9)
                c.drawRightString(w - margin, cy - 12, customer.get("name",""))
                c.drawRightString(w - margin, cy - 24, customer.get("address",""))
                c.drawRightString(w - margin, cy - 36, f"Phone: {customer.get('phone','')}")
                # table
                table_y = cy - 60
                c.setFont("Helvetica-Bold",9)
                c.drawString(margin, table_y, "Item")
                c.drawString(margin + 300, table_y, "Size")
                c.drawString(margin + 380, table_y, "Color")
                c.drawRightString(margin + 460 + 20, table_y, "Qty")
                c.drawRightString(margin + 520 + 60, table_y, "Unit")
                c.drawRightString(w - margin, table_y, "Total")
                c.line(margin, table_y-4, w - margin, table_y-4)
                ry = table_y - 18
                c.setFont("Helvetica",9)
                for it in items:
                    if ry < margin + 40:
                        c.showPage()
                        ry = h - margin - 40
                    c.drawString(margin, ry, str(it.get("item","")))
                    c.drawString(margin + 300, ry, str(it.get("size","")))
                    c.drawString(margin + 380, ry, str(it.get("color","")))
                    c.drawRightString(margin + 460 + 20, ry, str(it.get("qty","")))
                    c.drawRightString(margin + 520 + 60, ry, f"{float(it.get('unit',0.0)):.2f}")
                    total = int(it.get("qty",0)) * float(it.get("unit",0.0))
                    c.drawRightString(w - margin, ry, f"{total:.2f}")
                    ry -= 16
                # totals
                c.setFont("Helvetica",9)
                c.drawRightString(w - margin, ry - 10, f"Subtotal: {subtotal:.2f}")
                c.drawRightString(w - margin, ry - 26, f"Tax ({self.tax_percent}%): {tax_amt:.2f}")
                c.setFont("Helvetica-Bold",11)
                c.drawRightString(w - margin, ry - 46, f"Grand Total: {grand:.2f}")
                c.setFont("Helvetica",8)
                c.drawString(margin, margin + 10, "Payment terms: Due within 30 days.")
                c.save()
                messagebox.showinfo("Saved", f"Invoice exported to PDF:\n{pdf_path}")
                return
            except Exception as ex:
                print("PDF export failed:", ex)

        # fallback text export
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"{branding.get('business_name')}\n{branding.get('address')}\nPhone: {branding.get('phone')}\nEmail: {branding.get('email')}\n\n")
                f.write(f"Invoice: {self.invoice_no.get()}\nDate: {self.date_var.get()}\n\n")
                f.write("Billed To:\n")
                f.write(f"{customer.get('name','')}\n{customer.get('address','')}\nPhone: {customer.get('phone','')}\n\n")
                f.write(f"{'Item':40}{'Size':10}{'Color':10}{'Qty':6}{'Unit':12}{'Total':12}\n")
                f.write("-"*100 + "\n")
                for it in items:
                    qty = int(it.get("qty",0)); unit = float(it.get("unit",0.0)); total = qty*unit
                    f.write(f"{it.get('item','')[:40]:40}{it.get('size','')[:10]:10}{it.get('color','')[:10]:10}{qty:6}{unit:12.2f}{total:12.2f}\n")
                f.write("-"*100 + "\n")
                f.write(f"Subtotal: {subtotal:.2f}\nTax ({self.tax_percent}%): {tax_amt:.2f}\nGrand Total: {grand:.2f}\n")
            messagebox.showinfo("Saved", f"Invoice exported to:\n{txt_path}")
        except Exception as ex:
            messagebox.showerror("Export failed", str(ex))
# ...existing code...