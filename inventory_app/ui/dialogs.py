import tkinter as tk
from tkinter import ttk, messagebox
from .. import repository as repo

class AddColorDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Add Color")
        self.resizable(False, False)
        tk.Label(self, text="Color name").grid(row=0, column=0, padx=8, pady=8, sticky="e")
        self.e = tk.Entry(self, width=20)
        self.e.grid(row=0, column=1, padx=8, pady=8)
        ttk.Button(self, text="Save", command=self.save).grid(row=1, column=0, columnspan=2, pady=8)
        self.e.focus_set()

    def save(self):
        name = self.e.get().strip()
        if not name:
            messagebox.showerror("Error", "Color cannot be empty")
            return
        repo.add_color(name)
        messagebox.showinfo("Saved", f"Color '{name}' added")
        self.destroy()

class AddSizeDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Add Size")
        self.resizable(False, False)
        tk.Label(self, text="Size name").grid(row=0, column=0, padx=8, pady=8, sticky="e")
        self.e = tk.Entry(self, width=20)
        self.e.grid(row=0, column=1, padx=8, pady=8)
        ttk.Button(self, text="Save", command=self.save).grid(row=1, column=0, columnspan=2, pady=8)
        self.e.focus_set()

    def save(self):
        name = self.e.get().strip()
        if not name:
            messagebox.showerror("Error", "Size cannot be empty")
            return
        repo.add_size(name)
        messagebox.showinfo("Saved", f"Size '{name}' added")
        self.destroy()

class AddProductDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Add New Product")
        self.resizable(False, False)
        tk.Label(self, text="Product name").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        self.name_e = tk.Entry(self, width=26)
        self.name_e.grid(row=0, column=1, padx=8, pady=6)
        tk.Label(self, text="Rack number").grid(row=1, column=0, padx=8, pady=6, sticky="e")
        self.rack_e = tk.Entry(self, width=26)
        self.rack_e.grid(row=1, column=1, padx=8, pady=6)

        tk.Label(self, text="Color").grid(row=2, column=0, padx=8, pady=6, sticky="e")
        self.color_cb = ttk.Combobox(self, values=repo.list_colors(), width=23, state="readonly")
        self.color_cb.grid(row=2, column=1, padx=8, pady=6)

        tk.Label(self, text="Size").grid(row=3, column=0, padx=8, pady=6, sticky="e")
        self.size_cb = ttk.Combobox(self, values=repo.list_sizes(), width=23, state="readonly")
        self.size_cb.grid(row=3, column=1, padx=8, pady=6)

        tk.Label(self, text="Quantity").grid(row=4, column=0, padx=8, pady=6, sticky="e")
        self.qty_e = tk.Entry(self, width=26)
        self.qty_e.grid(row=4, column=1, padx=8, pady=6)

        tk.Label(self, text="Retail Price").grid(row=5, column=0, padx=8, pady=6, sticky="e")
        self.retail_e = tk.Entry(self, width=26)
        self.retail_e.grid(row=5, column=1, padx=8, pady=6)

        tk.Label(self, text="Wholesale Price").grid(row=6, column=0, padx=8, pady=6, sticky="e")
        self.wholesale_e = tk.Entry(self, width=26)
        self.wholesale_e.grid(row=6, column=1, padx=8, pady=6)

        ttk.Button(self, text="Save", command=self.save).grid(row=7, column=0, columnspan=2, pady=10)
        self.name_e.focus_set()

    def save(self):
        name = self.name_e.get().strip()
        rack = self.rack_e.get().strip()
        color = self.color_cb.get().strip()
        size = self.size_cb.get().strip()
        qty = self.qty_e.get().strip()
        retail = self.retail_e.get().strip()
        wholesale = self.wholesale_e.get().strip()
        if not (name and rack and color and size and qty and retail and wholesale):
            messagebox.showerror("Error", "All fields are required")
            return
        try:
            qty = int(qty); retail = float(retail); wholesale = float(wholesale)
        except ValueError:
            messagebox.showerror("Error", "Quantity must be integer; prices must be numbers")
            return

        color_id = repo.get_color_id(color)
        size_id = repo.get_size_id(size)
        pid = repo.get_or_create_product(name, rack)
        repo.add_variant(pid, color_id, size_id, qty, retail, wholesale)
        messagebox.showinfo("Saved", f"Product '{name}' added/updated")
        self.destroy()

class AddVariantDialog(tk.Toplevel):
    def __init__(self, master, product_id: int):
        super().__init__(master)
        self.title("Add Variant")
        self.product_id = product_id
        self.resizable(False, False)
        tk.Label(self, text="Color").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        self.color_cb = ttk.Combobox(self, values=repo.list_colors(), width=23, state="readonly")
        self.color_cb.grid(row=0, column=1, padx=8, pady=6)

        tk.Label(self, text="Size").grid(row=1, column=0, padx=8, pady=6, sticky="e")
        self.size_cb = ttk.Combobox(self, values=repo.list_sizes(), width=23, state="readonly")
        self.size_cb.grid(row=1, column=1, padx=8, pady=6)

        tk.Label(self, text="Quantity").grid(row=2, column=0, padx=8, pady=6, sticky="e")
        self.qty_e = tk.Entry(self, width=26)
        self.qty_e.grid(row=2, column=1, padx=8, pady=6)

        tk.Label(self, text="Retail Price").grid(row=3, column=0, padx=8, pady=6, sticky="e")
        self.retail_e = tk.Entry(self, width=26)
        self.retail_e.grid(row=3, column=1, padx=8, pady=6)

        tk.Label(self, text="Wholesale Price").grid(row=4, column=0, padx=8, pady=6, sticky="e")
        self.wholesale_e = tk.Entry(self, width=26)
        self.wholesale_e.grid(row=4, column=1, padx=8, pady=6)

        ttk.Button(self, text="Save", command=self.save).grid(row=5, column=0, columnspan=2, pady=10)

    def save(self):
        color = self.color_cb.get().strip()
        size = self.size_cb.get().strip()
        qty = self.qty_e.get().strip()
        retail = self.retail_e.get().strip()
        wholesale = self.wholesale_e.get().strip()
        if not (color and size and qty and retail and wholesale):
            messagebox.showerror("Error", "All fields are required")
            return
        try:
            qty = int(qty); retail = float(retail); wholesale = float(wholesale)
        except ValueError:
            messagebox.showerror("Error", "Quantity must be integer; prices must be numbers")
            return
        color_id = repo.get_color_id(color)
        size_id = repo.get_size_id(size)
        repo.add_variant(self.product_id, color_id, size_id, qty, retail, wholesale)
        messagebox.showinfo("Saved", "Variant added/updated")
        self.destroy()
