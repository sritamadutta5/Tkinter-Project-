"""
WanderList - Travel Bucket List and Planner
A desktop travel planning app built with Python + Tkinter (standard library only).

Run:  python wanderlist.py
Data is stored in wanderlist_data.json (same folder as this script).
Dates are entered as YYYY-MM-DD, times as HH:MM (24-hour).
"""

import json
import math
import os
import tkinter as tk
from datetime import datetime, date
from tkinter import ttk, messagebox

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "wanderlist_data.json")

GREEN = "#2F5D3A"
GREEN_DARK = "#244A2E"
GREEN_LIGHT = "#3F7A4D"
CREAM = "#FAF6EA"
BEIGE = "#E8DDC4"
BEIGE_DARK = "#D8CAA8"
TERRA = "#C8663A"
TERRA_DARK = "#A94F28"
TEXT = "#2B2B2B"
MUTED = "#6B6B5E"
WHITE = "#FFFFFF"
FONT = "Segoe UI"

CATEGORIES = ["Beach", "Mountains", "Adventure", "City", "Culture", "Other"]
PRIORITIES = ["High", "Medium", "Low"]
STATUSES = ["Wishlist", "Planned", "Visited"]
DEFAULT_PACKING = ["Clothes", "Travel documents", "ID proof",
                   "Chargers", "Medicines", "Toiletries"]
BUDGET_FIELDS = [("transport", "Transportation"),
                 ("accommodation", "Accommodation"),
                 ("food", "Food"),
                 ("activities", "Activities & Sightseeing"),
                 ("misc", "Miscellaneous")]

DATE_FMT = "%Y-%m-%d"
MAX_AMOUNT = 1_000_000_000


# ----------------------------------------------------------------------------
# Small helper functions
# ----------------------------------------------------------------------------
def parse_date(text):
    """Convert 'YYYY-MM-DD' to a date object (raises ValueError if invalid)."""
    return datetime.strptime(text.strip(), DATE_FMT).date()


def valid_time(text):
    try:
        datetime.strptime(text.strip(), "%H:%M")
        return True
    except ValueError:
        return False


def money(value):
    return f"\u20b9{value:,.2f}"


def parse_money(text, label):
    """Convert text to a non-negative float. Empty text counts as 0."""
    cleaned = text.replace(",", "").replace("\u20b9", "").strip()
    if cleaned == "":
        return 0.0
    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"{label} must be a number.")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be a non-negative number.")
    if value > MAX_AMOUNT:
        raise ValueError(f"{label} is too large.")
    return value


def shorten(text, n=50):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n - 3] + "..."


# ----------------------------------------------------------------------------
# JSON data storage
# ----------------------------------------------------------------------------
class DataStore:
    """Loads and saves all application data to a JSON file."""

    def __init__(self, path):
        self.path = path
        self.corrupt = False
        self.data = self.load()

    @staticmethod
    def default():
        return {"next_id": 1, "destinations": [], "trips": []}

    def load(self):
        if not os.path.exists(self.path):
            self.data = self.default()
            try:
                self.save()
            except OSError:
                pass
            return self.data
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError("Top level must be an object")
            return self.clean(raw)
        except (json.JSONDecodeError, ValueError, OSError):
            # Keep the broken file as a backup, then start fresh
            self.corrupt = True
            try:
                os.replace(self.path, self.path + ".bak")
            except OSError:
                pass
            return self.default()

    def clean(self, raw):
        """Make sure every record has the fields the app expects."""
        data = self.default()
        for d in raw.get("destinations", []):
            if not isinstance(d, dict) or "id" not in d or not d.get("name"):
                continue
            d.setdefault("country", "")
            d.setdefault("category", "Other")
            d.setdefault("priority", "Medium")
            d.setdefault("status", "Wishlist")
            d.setdefault("notes", "")
            d.setdefault("visit_date", "")
            d.setdefault("memory", "")
            data["destinations"].append(d)
        dest_ids = {d["id"] for d in data["destinations"]}
        for t in raw.get("trips", []):
            if not isinstance(t, dict) or "id" not in t or t.get("dest_id") not in dest_ids:
                continue
            t.setdefault("name", "Untitled trip")
            t.setdefault("start", "")
            t.setdefault("end", "")
            if not isinstance(t.get("activities"), list):
                t["activities"] = []
            if not isinstance(t.get("checklist"), list):
                t["checklist"] = []
            budget = t.get("budget") if isinstance(t.get("budget"), dict) else {}
            clean_budget = {}
            for key in [k for k, _ in BUDGET_FIELDS] + ["total"]:
                try:
                    clean_budget[key] = max(0.0, float(budget.get(key, 0)))
                except (TypeError, ValueError):
                    clean_budget[key] = 0.0
            t["budget"] = clean_budget
            data["trips"].append(t)
        ids = [d["id"] for d in data["destinations"]] + [t["id"] for t in data["trips"]]
        for t in data["trips"]:
            ids += [a.get("id", 0) for a in t["activities"] if isinstance(a, dict)]
        try:
            data["next_id"] = max(int(raw.get("next_id", 1)), max(ids, default=0) + 1)
        except (TypeError, ValueError):
            data["next_id"] = max(ids, default=0) + 1
        return data

    def save(self):
        """Write to a temp file first so a crash cannot corrupt the data."""
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)


# ----------------------------------------------------------------------------
# Main application
# ----------------------------------------------------------------------------
class WanderListApp(tk.Tk):
    PAGES = ["Dashboard", "My Bucket List", "Trip Planner",
             "Budget Planner", "Checklist & Memories"]

    def __init__(self):
        super().__init__()
        self.title("WanderList \u2013 Travel Bucket List and Planner")
        self.geometry("1180x780")
        self.minsize(1050, 700)
        self.configure(bg=CREAM)

        self.store = DataStore(DATA_FILE)
        self.d = self.store.data
        self.cur_trip_id = None      # trip selected in Trip Planner
        self.cur_dest_id = None      # destination selected in My Bucket List
        self.cur_act_id = None       # activity selected in itinerary

        self.setup_styles()
        self.build_layout()
        self.refresh_all()
        self.show_page("Dashboard")

        if self.store.corrupt:
            messagebox.showwarning(
                "Data file problem",
                "The saved data file could not be read, so a fresh one was started.\n"
                "The old file was kept as wanderlist_data.json.bak")

    # ------------------------------------------------------------------ data helpers
    def new_id(self):
        i = self.d["next_id"]
        self.d["next_id"] += 1
        return i

    def save(self):
        try:
            self.store.save()
            return True
        except OSError as e:
            messagebox.showerror("Save failed", f"Could not save data:\n{e}")
            return False

    def dest_by_id(self, i):
        return next((d for d in self.d["destinations"] if d["id"] == i), None)

    def trip_by_id(self, i):
        return next((t for t in self.d["trips"] if t["id"] == i), None)

    def trip_label(self, t):
        dest = self.dest_by_id(t["dest_id"])
        return f"{t['name']} ({dest['name'] if dest else '?'})"

    def sel_id(self, combo, items):
        idx = combo.current()
        return items[idx]["id"] if 0 <= idx < len(items) else None

    def refill_combo(self, combo, items, label_func):
        """Reload a combobox from a list of records, keeping the selection."""
        prev = self.sel_id(combo, self._combo_items.get(str(combo), []))
        combo["values"] = [label_func(x) for x in items]
        self._combo_items[str(combo)] = list(items)
        ids = [x["id"] for x in items]
        if prev in ids:
            combo.current(ids.index(prev))
        else:
            combo.set("")

    _combo_items = {}

    def combo_id(self, combo):
        return self.sel_id(combo, self._combo_items.get(str(combo), []))

    # ------------------------------------------------------------------ styling
    def setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame", background=CREAM)
        s.configure("White.TFrame", background=WHITE)
        s.configure("TLabel", background=CREAM, foreground=TEXT, font=(FONT, 10))
        s.configure("Title.TLabel", font=(FONT, 20, "bold"), foreground=GREEN)
        s.configure("Sub.TLabel", foreground=MUTED, font=(FONT, 10))
        s.configure("TLabelframe", background=CREAM, bordercolor=BEIGE_DARK)
        s.configure("TLabelframe.Label", background=CREAM, foreground=GREEN,
                    font=(FONT, 11, "bold"))
        s.configure("TButton", font=(FONT, 10, "bold"), padding=(12, 6),
                    background=GREEN, foreground=WHITE, borderwidth=0, focusthickness=0)
        s.map("TButton", background=[("active", GREEN_DARK)])
        s.configure("Accent.TButton", background=TERRA)
        s.map("Accent.TButton", background=[("active", TERRA_DARK)])
        s.configure("Beige.TButton", background=BEIGE, foreground=TEXT)
        s.map("Beige.TButton", background=[("active", BEIGE_DARK)])
        s.configure("TEntry", fieldbackground=WHITE, padding=4)
        s.configure("TCombobox", fieldbackground=WHITE, padding=4)
        s.configure("Treeview", font=(FONT, 10), rowheight=26,
                    background=WHITE, fieldbackground=WHITE, bordercolor=BEIGE_DARK)
        s.configure("Treeview.Heading", background=GREEN, foreground=WHITE,
                    font=(FONT, 10, "bold"), padding=5)
        s.map("Treeview.Heading", background=[("active", GREEN_DARK)])
        s.map("Treeview", background=[("selected", BEIGE)],
              foreground=[("selected", TEXT)])
        s.configure("TCheckbutton", background=CREAM, font=(FONT, 11))
        s.configure("TNotebook", background=CREAM, borderwidth=0)
        s.configure("TNotebook.Tab", font=(FONT, 10, "bold"), padding=(16, 7),
                    background=BEIGE, foreground=TEXT)
        s.map("TNotebook.Tab", background=[("selected", GREEN)],
              foreground=[("selected", WHITE)])
        s.configure("Horizontal.TProgressbar", troughcolor=BEIGE,
                    background=GREEN, thickness=18)

    # ------------------------------------------------------------------ layout
    def build_layout(self):
        self.sidebar = tk.Frame(self, bg=GREEN, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="\u2708  WanderList", bg=GREEN, fg=WHITE,
                 font=(FONT, 18, "bold")).pack(pady=(28, 2))
        tk.Label(self.sidebar, text="Travel Bucket List & Planner", bg=GREEN,
                 fg=BEIGE, font=(FONT, 9)).pack(pady=(0, 28))

        self.nav_buttons = {}
        for name in self.PAGES:
            b = tk.Button(self.sidebar, text=name, anchor="w", bg=GREEN, fg=WHITE,
                          activebackground=GREEN_LIGHT, activeforeground=WHITE,
                          relief="flat", bd=0, font=(FONT, 11), padx=24, pady=11,
                          cursor="hand2", command=lambda n=name: self.show_page(n))
            b.pack(fill="x")
            self.nav_buttons[name] = b

        self.container = ttk.Frame(self)
        self.container.pack(side="right", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.pages = {}
        builders = [self.build_dashboard, self.build_bucket, self.build_planner,
                    self.build_budget, self.build_extras]
        for name, build in zip(self.PAGES, builders):
            frame = ttk.Frame(self.container, padding=(26, 18))
            frame.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = frame
            build(frame)

    def show_page(self, name):
        self.refresh_all()
        self.pages[name].tkraise()
        for n, b in self.nav_buttons.items():
            b.configure(bg=GREEN_LIGHT if n == name else GREEN)

    # ------------------------------------------------------------------ widget helpers
    def header(self, parent, title, subtitle):
        ttk.Label(parent, text=title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text=subtitle, style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

    def btn(self, parent, text, command, style="TButton"):
        return ttk.Button(parent, text=text, command=command, style=style, cursor="hand2")

    def field(self, parent, label, row, col, var, values=None, width=22, colspan=1):
        ttk.Label(parent, text=label).grid(row=row, column=col * 2, sticky="w",
                                           padx=(10, 6), pady=5)
        if values is not None:
            w = ttk.Combobox(parent, textvariable=var, values=values,
                             state="readonly", width=width)
        else:
            w = ttk.Entry(parent, textvariable=var, width=width)
        w.grid(row=row, column=col * 2 + 1, sticky="ew", padx=(0, 12), pady=5,
               columnspan=colspan)
        return w

    def make_tree(self, parent, cols, widths, height):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=height,
                            selectmode="browse")
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return frame, tree

    # ================================================================== DASHBOARD
    def build_dashboard(self, page):
        self.header(page, "Dashboard", "A quick summary of your travel plans")

        cards = ttk.Frame(page)
        cards.pack(fill="x", pady=(4, 14))
        self.stat_labels = {}
        for i, (key, caption) in enumerate([
                ("total", "Destinations Saved"), ("visited", "Destinations Visited"),
                ("upcoming", "Upcoming Trips"), ("budget", "Total Travel Budget")]):
            card = tk.Frame(cards, bg=WHITE, highlightthickness=1,
                            highlightbackground=BEIGE_DARK, padx=16, pady=14)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            cards.grid_columnconfigure(i, weight=1, uniform="cards")
            lbl = tk.Label(card, text="0", bg=WHITE, fg=GREEN if i != 2 else TERRA,
                           font=(FONT, 22, "bold"))
            lbl.pack(anchor="w")
            tk.Label(card, text=caption, bg=WHITE, fg=MUTED, font=(FONT, 10)).pack(anchor="w")
            self.stat_labels[key] = lbl

        lower = ttk.Frame(page)
        lower.pack(fill="both", expand=True)

        left = ttk.LabelFrame(lower, text="Recently Added Destinations", padding=10)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        frame, self.recent_tree = self.make_tree(
            left, ("Destination", "Country", "Category", "Status"), (170, 120, 100, 90), 8)
        frame.pack(fill="both", expand=True)

        right = ttk.LabelFrame(lower, text="Quick Navigation", padding=14)
        right.pack(side="right", fill="y")
        for name in self.PAGES[1:]:
            self.btn(right, name, lambda n=name: self.show_page(n),
                     "Accent.TButton" if name == "My Bucket List" else "TButton"
                     ).pack(fill="x", pady=6, ipadx=20)

    def refresh_dashboard(self):
        dests = self.d["destinations"]
        today = date.today()
        upcoming = 0
        budget_total = 0.0
        for t in self.d["trips"]:
            budget_total += t["budget"].get("total", 0.0)
            try:
                if parse_date(t["end"]) >= today:
                    upcoming += 1
            except ValueError:
                pass
        self.stat_labels["total"].config(text=str(len(dests)))
        self.stat_labels["visited"].config(
            text=str(sum(1 for d in dests if d["status"] == "Visited")))
        self.stat_labels["upcoming"].config(text=str(upcoming))
        self.stat_labels["budget"].config(text=money(budget_total))

        self.recent_tree.delete(*self.recent_tree.get_children())
        for d in list(reversed(dests))[:6]:
            self.recent_tree.insert("", "end", values=(d["name"], d["country"],
                                                       d["category"], d["status"]))

    # ================================================================== BUCKET LIST
    def build_bucket(self, page):
        self.header(page, "My Bucket List", "Save, edit and search your dream destinations")

        form = ttk.LabelFrame(page, text="Destination Details", padding=8)
        form.pack(fill="x")
        for c in (1, 3):
            form.grid_columnconfigure(c, weight=1)
        self.b_name, self.b_country = tk.StringVar(), tk.StringVar()
        self.b_cat = tk.StringVar(value=CATEGORIES[0])
        self.b_pri = tk.StringVar(value="Medium")
        self.b_status = tk.StringVar(value="Wishlist")
        self.b_notes = tk.StringVar()
        self.field(form, "Destination *", 0, 0, self.b_name)
        self.field(form, "Country *", 0, 1, self.b_country)
        self.field(form, "Category", 1, 0, self.b_cat, CATEGORIES)
        self.field(form, "Priority", 1, 1, self.b_pri, PRIORITIES)
        self.field(form, "Status", 2, 0, self.b_status, STATUSES)
        self.field(form, "Note", 2, 1, self.b_notes)

        row = ttk.Frame(form)
        row.grid(row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(6, 2))
        self.btn(row, "Add Destination", self.add_destination).pack(side="left", padx=(0, 8))
        self.btn(row, "Update Selected", self.update_destination, "Accent.TButton").pack(side="left", padx=(0, 8))
        self.btn(row, "Delete Selected", self.delete_destination, "Beige.TButton").pack(side="left", padx=(0, 8))
        self.btn(row, "Clear Form", self.clear_bucket_form, "Beige.TButton").pack(side="left")

        bar = ttk.Frame(page)
        bar.pack(fill="x", pady=(12, 6))
        ttk.Label(bar, text="Search:").pack(side="left")
        self.f_search = tk.StringVar()
        self.f_search.trace_add("write", lambda *_: self.refresh_bucket())
        ttk.Entry(bar, textvariable=self.f_search, width=24).pack(side="left", padx=(6, 16))
        ttk.Label(bar, text="Category:").pack(side="left")
        self.f_cat = tk.StringVar(value="All")
        c1 = ttk.Combobox(bar, textvariable=self.f_cat, values=["All"] + CATEGORIES,
                          state="readonly", width=12)
        c1.pack(side="left", padx=(6, 16))
        ttk.Label(bar, text="Status:").pack(side="left")
        self.f_status = tk.StringVar(value="All")
        c2 = ttk.Combobox(bar, textvariable=self.f_status, values=["All"] + STATUSES,
                          state="readonly", width=12)
        c2.pack(side="left", padx=(6, 16))
        for c in (c1, c2):
            c.bind("<<ComboboxSelected>>", lambda e: self.refresh_bucket())
        self.btn(bar, "Clear Filters", self.clear_filters, "Beige.TButton").pack(side="left")
        self.count_lbl = ttk.Label(bar, text="", style="Sub.TLabel")
        self.count_lbl.pack(side="right")

        frame, self.bucket_tree = self.make_tree(
            page, ("Destination", "Country", "Category", "Priority", "Status", "Note"),
            (160, 120, 100, 80, 90, 300), 10)
        frame.pack(fill="both", expand=True)
        self.bucket_tree.bind("<<TreeviewSelect>>", self.on_bucket_select)

    def read_bucket_form(self, editing_id=None):
        name = self.b_name.get().strip()
        country = self.b_country.get().strip()
        if not name:
            messagebox.showerror("Missing information", "Please enter the destination name.")
            return None
        if not country:
            messagebox.showerror("Missing information", "Please enter the country.")
            return None
        if len(name) > 60 or len(country) > 60:
            messagebox.showerror("Too long", "Name and country must be 60 characters or fewer.")
            return None
        for d in self.d["destinations"]:
            if (d["id"] != editing_id and d["name"].lower() == name.lower()
                    and d["country"].lower() == country.lower()):
                messagebox.showerror("Duplicate", f"{name}, {country} is already on your list.")
                return None
        return {"name": name, "country": country, "category": self.b_cat.get(),
                "priority": self.b_pri.get(), "status": self.b_status.get(),
                "notes": self.b_notes.get().strip()[:300]}

    def add_destination(self):
        info = self.read_bucket_form()
        if not info:
            return
        info.update({"id": self.new_id(), "visit_date": "", "memory": ""})
        self.d["destinations"].append(info)
        if self.save():
            self.clear_bucket_form()
            self.refresh_all()
            messagebox.showinfo("Added", f"{info['name']} was added to your bucket list.")

    def update_destination(self):
        dest = self.dest_by_id(self.cur_dest_id)
        if not dest:
            messagebox.showwarning("No selection", "Select a destination from the table first.")
            return
        info = self.read_bucket_form(editing_id=dest["id"])
        if not info:
            return
        dest.update(info)
        if self.save():
            self.refresh_all()
            messagebox.showinfo("Updated", "Destination updated successfully.")

    def delete_destination(self):
        dest = self.dest_by_id(self.cur_dest_id)
        if not dest:
            messagebox.showwarning("No selection", "Select a destination from the table first.")
            return
        linked = [t for t in self.d["trips"] if t["dest_id"] == dest["id"]]
        msg = f"Delete '{dest['name']}'?"
        if linked:
            msg += f"\n\n{len(linked)} trip(s) to this destination (with their itineraries, budgets and checklists) will also be deleted."
        if not messagebox.askyesno("Confirm delete", msg, icon="warning"):
            return
        self.d["destinations"].remove(dest)
        for t in linked:
            self.d["trips"].remove(t)
        if self.cur_trip_id and not self.trip_by_id(self.cur_trip_id):
            self.cur_trip_id = None
        if self.save():
            self.clear_bucket_form()
            self.refresh_all()
            messagebox.showinfo("Deleted", "Destination deleted.")

    def clear_bucket_form(self):
        self.cur_dest_id = None
        self.b_name.set("")
        self.b_country.set("")
        self.b_cat.set(CATEGORIES[0])
        self.b_pri.set("Medium")
        self.b_status.set("Wishlist")
        self.b_notes.set("")
        if hasattr(self, "bucket_tree"):
            self.bucket_tree.selection_set(())

    def clear_filters(self):
        self.f_search.set("")
        self.f_cat.set("All")
        self.f_status.set("All")
        self.refresh_bucket()

    def on_bucket_select(self, _event=None):
        sel = self.bucket_tree.selection()
        if not sel:
            return
        dest = self.dest_by_id(int(sel[0]))
        if not dest:
            return
        self.cur_dest_id = dest["id"]
        self.b_name.set(dest["name"])
        self.b_country.set(dest["country"])
        self.b_cat.set(dest["category"])
        self.b_pri.set(dest["priority"])
        self.b_status.set(dest["status"])
        self.b_notes.set(dest["notes"])

    def refresh_bucket(self):
        q = self.f_search.get().strip().lower()
        cat, status = self.f_cat.get(), self.f_status.get()
        tree = self.bucket_tree
        tree.delete(*tree.get_children())
        shown = 0
        for d in self.d["destinations"]:
            if q and q not in d["name"].lower() and q not in d["country"].lower():
                continue
            if cat != "All" and d["category"] != cat:
                continue
            if status != "All" and d["status"] != status:
                continue
            tree.insert("", "end", iid=str(d["id"]),
                        values=(d["name"], d["country"], d["category"], d["priority"],
                                d["status"], shorten(d["notes"], 60)))
            shown += 1
        self.count_lbl.config(text=f"Showing {shown} of {len(self.d['destinations'])}")
        if self.cur_dest_id is not None and tree.exists(str(self.cur_dest_id)):
            tree.selection_set(str(self.cur_dest_id))

    # ================================================================== TRIP PLANNER
    def build_planner(self, page):
        self.header(page, "Trip Planner & Itinerary",
                    "Create trips from your bucket list and plan each day")

        form = ttk.LabelFrame(page, text="Trip Details", padding=6)
        form.pack(fill="x")
        for c in (1, 3):
            form.grid_columnconfigure(c, weight=1)
        self.t_dest = ttk.Combobox(form, state="readonly", width=22)
        ttk.Label(form, text="Destination *").grid(row=0, column=0, sticky="w", padx=(10, 6), pady=4)
        self.t_dest.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=4)
        self.t_name, self.t_start, self.t_end = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.field(form, "Trip Name *", 0, 1, self.t_name)
        self.field(form, "Start (YYYY-MM-DD) *", 1, 0, self.t_start)
        self.field(form, "End (YYYY-MM-DD) *", 1, 1, self.t_end)
        row = ttk.Frame(form)
        row.grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=(4, 2))
        self.btn(row, "Create Trip", self.create_trip).pack(side="left", padx=(0, 8))
        self.btn(row, "Update Selected Trip", self.update_trip, "Accent.TButton").pack(side="left", padx=(0, 8))
        self.btn(row, "Delete Selected Trip", self.delete_trip, "Beige.TButton").pack(side="left", padx=(0, 8))
        self.btn(row, "Clear", self.clear_trip_form, "Beige.TButton").pack(side="left")

        frame, self.trip_tree = self.make_tree(
            page, ("Trip", "Destination", "Start", "End", "Days", "Activities"),
            (210, 170, 100, 100, 60, 80), 4)
        frame.pack(fill="x", pady=(10, 8))
        self.trip_tree.bind("<<TreeviewSelect>>", self.on_trip_select)

        self.itin_box = ttk.LabelFrame(page, text="Itinerary", padding=6)
        self.itin_box.pack(fill="both", expand=True)
        for c in (1, 3):
            self.itin_box.grid_columnconfigure(c, weight=1)
        self.a_date, self.a_time = tk.StringVar(), tk.StringVar()
        self.a_name, self.a_desc = tk.StringVar(), tk.StringVar()
        self.field(self.itin_box, "Date *", 0, 0, self.a_date)
        self.field(self.itin_box, "Time (HH:MM) *", 0, 1, self.a_time)
        self.field(self.itin_box, "Activity *", 1, 0, self.a_name)
        self.field(self.itin_box, "Description", 1, 1, self.a_desc)
        row = ttk.Frame(self.itin_box)
        row.grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=(4, 6))
        self.btn(row, "Add Activity", self.add_activity).pack(side="left", padx=(0, 8))
        self.btn(row, "Update Selected", self.update_activity, "Accent.TButton").pack(side="left", padx=(0, 8))
        self.btn(row, "Delete Selected", self.delete_activity, "Beige.TButton").pack(side="left", padx=(0, 8))
        self.btn(row, "Clear", self.clear_activity_form, "Beige.TButton").pack(side="left")
        frame, self.act_tree = self.make_tree(
            self.itin_box, ("Date", "Time", "Activity", "Description"), (100, 70, 220, 380), 5)
        frame.grid(row=3, column=0, columnspan=4, sticky="nsew", padx=6)
        self.itin_box.grid_rowconfigure(3, weight=1)
        self.act_tree.bind("<<TreeviewSelect>>", self.on_activity_select)

    def read_trip_form(self):
        dest_id = self.combo_id(self.t_dest)
        name = self.t_name.get().strip()
        if dest_id is None:
            messagebox.showerror("Missing information", "Please select a destination.\n(Add one in My Bucket List first if the list is empty.)")
            return None
        if not name:
            messagebox.showerror("Missing information", "Please enter a trip name.")
            return None
        if len(name) > 60:
            messagebox.showerror("Too long", "Trip name must be 60 characters or fewer.")
            return None
        try:
            start = parse_date(self.t_start.get())
            end = parse_date(self.t_end.get())
        except ValueError:
            messagebox.showerror("Invalid date", "Enter dates in YYYY-MM-DD format (for example 2026-12-25).")
            return None
        if end < start:
            messagebox.showerror("Invalid dates", "The ending date cannot be earlier than the starting date.")
            return None
        return dest_id, name, start, end

    def create_trip(self):
        info = self.read_trip_form()
        if not info:
            return
        dest_id, name, start, end = info
        trip = {"id": self.new_id(), "name": name, "dest_id": dest_id,
                "start": start.strftime(DATE_FMT), "end": end.strftime(DATE_FMT),
                "activities": [], "checklist": [],
                "budget": {k: 0.0 for k, _ in BUDGET_FIELDS} | {"total": 0.0}}
        self.d["trips"].append(trip)
        dest = self.dest_by_id(dest_id)
        if dest and dest["status"] == "Wishlist":
            dest["status"] = "Planned"
        if self.save():
            self.cur_trip_id = trip["id"]
            self.refresh_all()
            messagebox.showinfo("Trip created", f"'{name}' has been created. You can now add itinerary activities below.")

    def update_trip(self):
        trip = self.trip_by_id(self.cur_trip_id)
        if not trip:
            messagebox.showwarning("No selection", "Select a trip from the table first.")
            return
        info = self.read_trip_form()
        if not info:
            return
        dest_id, name, start, end = info
        outside = []
        for a in trip["activities"]:
            try:
                if not start <= parse_date(a["date"]) <= end:
                    outside.append(a["name"])
            except ValueError:
                pass
        if outside:
            messagebox.showerror("Dates conflict",
                                 "These activities fall outside the new dates:\n- " + "\n- ".join(outside[:5]) +
                                 "\n\nEdit or delete them first.")
            return
        trip.update({"name": name, "dest_id": dest_id,
                     "start": start.strftime(DATE_FMT), "end": end.strftime(DATE_FMT)})
        if self.save():
            self.refresh_all()
            messagebox.showinfo("Updated", "Trip updated successfully.")

    def delete_trip(self):
        trip = self.trip_by_id(self.cur_trip_id)
        if not trip:
            messagebox.showwarning("No selection", "Select a trip from the table first.")
            return
        if not messagebox.askyesno(
                "Confirm delete",
                f"Delete trip '{trip['name']}'?\nIts itinerary, budget and checklist will also be deleted.",
                icon="warning"):
            return
        self.d["trips"].remove(trip)
        self.cur_trip_id = None
        if self.save():
            self.clear_trip_form()
            self.refresh_all()
            messagebox.showinfo("Deleted", "Trip deleted.")

    def clear_trip_form(self):
        self.cur_trip_id = None
        self.cur_act_id = None
        self.t_dest.set("")
        for v in (self.t_name, self.t_start, self.t_end):
            v.set("")
        self.trip_tree.selection_set(())
        self.clear_activity_form()
        self.refresh_itinerary()

    def on_trip_select(self, _event=None):
        sel = self.trip_tree.selection()
        if not sel:
            return
        trip = self.trip_by_id(int(sel[0]))
        if not trip:
            return
        self.cur_trip_id = trip["id"]
        dests = self.d["destinations"]
        ids = [d["id"] for d in dests]
        if trip["dest_id"] in ids:
            self.t_dest.current(ids.index(trip["dest_id"]))
        self.t_name.set(trip["name"])
        self.t_start.set(trip["start"])
        self.t_end.set(trip["end"])
        self.cur_act_id = None
        self.clear_activity_form()
        self.refresh_itinerary()

    def refresh_planner(self):
        self.refill_combo(self.t_dest, self.d["destinations"],
                          lambda d: f"{d['name']}, {d['country']}")
        tree = self.trip_tree
        tree.delete(*tree.get_children())
        for t in self.d["trips"]:
            dest = self.dest_by_id(t["dest_id"])
            try:
                days = (parse_date(t["end"]) - parse_date(t["start"])).days + 1
            except ValueError:
                days = "?"
            tree.insert("", "end", iid=str(t["id"]),
                        values=(t["name"], dest["name"] if dest else "?", t["start"],
                                t["end"], days, len(t["activities"])))
        if self.cur_trip_id is not None and not tree.exists(str(self.cur_trip_id)):
            self.cur_trip_id = None
        if self.cur_trip_id is not None:
            tree.selection_set(str(self.cur_trip_id))
        self.refresh_itinerary()

    # ---- itinerary
    def refresh_itinerary(self):
        trip = self.trip_by_id(self.cur_trip_id)
        self.itin_box.config(text=f"Itinerary \u2013 {trip['name']}" if trip
                             else "Itinerary (select a trip above)")
        self.act_tree.delete(*self.act_tree.get_children())
        if not trip:
            return
        for a in sorted(trip["activities"], key=lambda a: (a["date"], a["time"])):
            self.act_tree.insert("", "end", iid=str(a["id"]),
                                 values=(a["date"], a["time"], a["name"], shorten(a["desc"], 80)))
        if self.cur_act_id is not None and self.act_tree.exists(str(self.cur_act_id)):
            self.act_tree.selection_set(str(self.cur_act_id))

    def read_activity_form(self, trip):
        name = self.a_name.get().strip()
        time_text = self.a_time.get().strip()
        if not name:
            messagebox.showerror("Missing information", "Please enter the activity name.")
            return None
        try:
            day = parse_date(self.a_date.get())
        except ValueError:
            messagebox.showerror("Invalid date", "Enter the activity date as YYYY-MM-DD.")
            return None
        if not valid_time(time_text):
            messagebox.showerror("Invalid time", "Enter the time as HH:MM in 24-hour format (for example 09:30).")
            return None
        if not parse_date(trip["start"]) <= day <= parse_date(trip["end"]):
            messagebox.showerror("Date outside trip",
                                 f"The activity date must be between {trip['start']} and {trip['end']}.")
            return None
        t = datetime.strptime(time_text, "%H:%M").strftime("%H:%M")
        return {"date": day.strftime(DATE_FMT), "time": t, "name": name[:80],
                "desc": self.a_desc.get().strip()[:300]}

    def add_activity(self):
        trip = self.trip_by_id(self.cur_trip_id)
        if not trip:
            messagebox.showwarning("No trip selected", "Select or create a trip first.")
            return
        info = self.read_activity_form(trip)
        if not info:
            return
        info["id"] = self.new_id()
        trip["activities"].append(info)
        if self.save():
            self.clear_activity_form()
            self.refresh_all()

    def update_activity(self):
        trip = self.trip_by_id(self.cur_trip_id)
        act = next((a for a in trip["activities"] if a["id"] == self.cur_act_id), None) if trip else None
        if not act:
            messagebox.showwarning("No selection", "Select an activity from the itinerary table first.")
            return
        info = self.read_activity_form(trip)
        if not info:
            return
        act.update(info)
        if self.save():
            self.refresh_all()
            messagebox.showinfo("Updated", "Activity updated.")

    def delete_activity(self):
        trip = self.trip_by_id(self.cur_trip_id)
        act = next((a for a in trip["activities"] if a["id"] == self.cur_act_id), None) if trip else None
        if not act:
            messagebox.showwarning("No selection", "Select an activity from the itinerary table first.")
            return
        if not messagebox.askyesno("Confirm delete", f"Delete activity '{act['name']}'?"):
            return
        trip["activities"].remove(act)
        if self.save():
            self.clear_activity_form()
            self.refresh_all()

    def clear_activity_form(self):
        self.cur_act_id = None
        for v in (self.a_date, self.a_time, self.a_name, self.a_desc):
            v.set("")
        if hasattr(self, "act_tree"):
            self.act_tree.selection_set(())

    def on_activity_select(self, _event=None):
        sel = self.act_tree.selection()
        trip = self.trip_by_id(self.cur_trip_id)
        if not sel or not trip:
            return
        act = next((a for a in trip["activities"] if a["id"] == int(sel[0])), None)
        if not act:
            return
        self.cur_act_id = act["id"]
        self.a_date.set(act["date"])
        self.a_time.set(act["time"])
        self.a_name.set(act["name"])
        self.a_desc.set(act["desc"])

    # ================================================================== BUDGET
    def build_budget(self, page):
        self.header(page, "Travel Budget Planner",
                    "Estimate trip costs in Indian Rupees (\u20b9) and check them against your budget")

        top = ttk.Frame(page)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Select Trip:").pack(side="left")
        self.bd_combo = ttk.Combobox(top, state="readonly", width=40)
        self.bd_combo.pack(side="left", padx=8)
        self.bd_combo.bind("<<ComboboxSelected>>", lambda e: self.load_budget())

        body = ttk.Frame(page)
        body.pack(fill="x")
        form = ttk.LabelFrame(body, text="Estimated Expenses (\u20b9)", padding=12)
        form.pack(side="left", fill="y", padx=(0, 14))
        self.bd_vars = {}
        for i, (key, label) in enumerate(BUDGET_FIELDS + [("total", "Total Estimated Budget")]):
            ttk.Label(form, text=label + ":").grid(row=i, column=0, sticky="w", padx=6, pady=6)
            var = tk.StringVar()
            var.trace_add("write", lambda *_: self.update_budget_display())
            ttk.Entry(form, textvariable=var, width=18, justify="right").grid(row=i, column=1, padx=6, pady=6)
            self.bd_vars[key] = var
        row = ttk.Frame(form)
        row.grid(row=6, column=0, columnspan=2, pady=(10, 0))
        self.btn(row, "Save Budget", self.save_budget, "Accent.TButton").pack(side="left", padx=4)
        self.btn(row, "Clear Fields", self.clear_budget_fields, "Beige.TButton").pack(side="left", padx=4)

        res = tk.Frame(body, bg=WHITE, highlightthickness=1, highlightbackground=BEIGE_DARK,
                       padx=24, pady=18)
        res.pack(side="left", fill="both", expand=True)
        tk.Label(res, text="Budget Summary", bg=WHITE, fg=GREEN, font=(FONT, 13, "bold")).pack(anchor="w", pady=(0, 14))
        self.bd_out = {}
        for key, caption in [("exp", "Total Estimated Expenses"), ("budget", "Total Budget"),
                             ("rem", "Remaining Budget")]:
            tk.Label(res, text=caption, bg=WHITE, fg=MUTED, font=(FONT, 10)).pack(anchor="w")
            lbl = tk.Label(res, text="\u2014", bg=WHITE, fg=TEXT, font=(FONT, 20, "bold"))
            lbl.pack(anchor="w", pady=(0, 12))
            self.bd_out[key] = lbl
        self.bd_status = tk.Label(res, text="Select a trip to begin", bg=WHITE, fg=MUTED,
                                  font=(FONT, 13, "bold"))
        self.bd_status.pack(anchor="w", pady=(4, 0))

    def read_budget(self):
        values = {}
        for key, label in BUDGET_FIELDS + [("total", "Total Estimated Budget")]:
            values[key] = parse_money(self.bd_vars[key].get(), label)
        return values

    def update_budget_display(self):
        if not hasattr(self, "bd_out"):
            return
        try:
            v = self.read_budget()
        except ValueError as e:
            for lbl in self.bd_out.values():
                lbl.config(text="\u2014", fg=TEXT)
            self.bd_status.config(text=str(e), fg=TERRA)
            return
        expenses = sum(v[k] for k, _ in BUDGET_FIELDS)
        remaining = v["total"] - expenses
        self.bd_out["exp"].config(text=money(expenses))
        self.bd_out["budget"].config(text=money(v["total"]))
        self.bd_out["rem"].config(text=money(remaining), fg=GREEN if remaining >= 0 else TERRA)
        if remaining >= 0:
            self.bd_status.config(text="\u2714 Within budget", fg=GREEN)
        else:
            self.bd_status.config(text=f"\u26a0 Over budget by {money(-remaining)}", fg=TERRA)

    def load_budget(self):
        trip = self.trip_by_id(self.combo_id(self.bd_combo))
        if not trip:
            self.clear_budget_fields()
            return
        for key, var in self.bd_vars.items():
            amount = trip["budget"].get(key, 0.0)
            var.set(f"{amount:g}" if amount else "")
        self.update_budget_display()

    def save_budget(self):
        trip = self.trip_by_id(self.combo_id(self.bd_combo))
        if not trip:
            messagebox.showwarning("No trip selected", "Select a trip first. (Create one in Trip Planner if none exist.)")
            return
        try:
            trip["budget"] = self.read_budget()
        except ValueError as e:
            messagebox.showerror("Invalid amount", str(e))
            return
        if self.save():
            self.refresh_dashboard()
            messagebox.showinfo("Saved", f"Budget saved for '{trip['name']}'.")

    def clear_budget_fields(self):
        for var in self.bd_vars.values():
            var.set("")
        self.update_budget_display()
        if not self.combo_id(self.bd_combo):
            self.bd_status.config(text="Select a trip to begin", fg=MUTED)

    def refresh_budget(self):
        before = self.combo_id(self.bd_combo)
        self.refill_combo(self.bd_combo, self.d["trips"], self.trip_label)
        if self.combo_id(self.bd_combo) != before or before is None:
            self.load_budget()

    # ================================================================== CHECKLIST + MEMORIES
    def build_extras(self, page):
        self.header(page, "Trip Checklist & Travel Memories",
                    "Pack smart before you go, remember fondly after you return")
        nb = ttk.Notebook(page)
        nb.pack(fill="both", expand=True)
        tab1 = ttk.Frame(nb, padding=14)
        tab2 = ttk.Frame(nb, padding=14)
        nb.add(tab1, text="  Trip Checklist  ")
        nb.add(tab2, text="  Travel Memories  ")
        self.build_checklist(tab1)
        self.build_memories(tab2)

    # ---- A. checklist
    def build_checklist(self, tab):
        top = ttk.Frame(tab)
        top.pack(fill="x")
        ttk.Label(top, text="Select Trip:").pack(side="left")
        self.cl_combo = ttk.Combobox(top, state="readonly", width=38)
        self.cl_combo.pack(side="left", padx=8)
        self.cl_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_checklist())
        ttk.Label(top, text="Show:").pack(side="left", padx=(16, 4))
        self.cl_filter = tk.StringVar(value="All")
        f = ttk.Combobox(top, textvariable=self.cl_filter, values=["All", "Pending", "Completed"],
                         state="readonly", width=11)
        f.pack(side="left")
        f.bind("<<ComboboxSelected>>", lambda e: self.refresh_checklist())

        add = ttk.Frame(tab)
        add.pack(fill="x", pady=10)
        self.cl_new = tk.StringVar()
        entry = ttk.Entry(add, textvariable=self.cl_new, width=36)
        entry.pack(side="left")
        entry.bind("<Return>", lambda e: self.add_item())
        self.btn(add, "Add Item", self.add_item).pack(side="left", padx=8)
        self.btn(add, "Add Default Suggestions", self.add_default_items, "Accent.TButton").pack(side="left")

        prog = ttk.Frame(tab)
        prog.pack(fill="x", pady=(0, 8))
        self.cl_bar = ttk.Progressbar(prog, maximum=100, length=300)
        self.cl_bar.pack(side="left")
        self.cl_stat = ttk.Label(prog, text="", font=(FONT, 10, "bold"))
        self.cl_stat.pack(side="left", padx=12)

        holder = tk.Frame(tab, bg=WHITE, highlightthickness=1, highlightbackground=BEIGE_DARK)
        holder.pack(fill="both", expand=True)
        self.cl_canvas = tk.Canvas(holder, bg=WHITE, highlightthickness=0)
        sb = ttk.Scrollbar(holder, orient="vertical", command=self.cl_canvas.yview)
        self.cl_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.cl_canvas.pack(side="left", fill="both", expand=True)
        self.cl_inner = tk.Frame(self.cl_canvas, bg=WHITE)
        win = self.cl_canvas.create_window((0, 0), window=self.cl_inner, anchor="nw")
        self.cl_inner.bind("<Configure>", lambda e: self.cl_canvas.configure(
            scrollregion=self.cl_canvas.bbox("all")))
        self.cl_canvas.bind("<Configure>", lambda e: self.cl_canvas.itemconfig(win, width=e.width))
        self.cl_canvas.bind("<Enter>", lambda e: self.cl_canvas.bind_all(
            "<MouseWheel>", lambda ev: self.cl_canvas.yview_scroll(int(-ev.delta / 120), "units")))
        self.cl_canvas.bind("<Leave>", lambda e: self.cl_canvas.unbind_all("<MouseWheel>"))

    def cl_trip(self):
        return self.trip_by_id(self.combo_id(self.cl_combo))

    def add_item(self):
        trip = self.cl_trip()
        if not trip:
            messagebox.showwarning("No trip selected", "Select a trip first.")
            return
        text = self.cl_new.get().strip()
        if not text:
            messagebox.showerror("Missing information", "Type an item name first.")
            return
        if any(i["text"].lower() == text.lower() for i in trip["checklist"]):
            messagebox.showerror("Duplicate", "That item is already on the checklist.")
            return
        trip["checklist"].append({"text": text[:80], "done": False})
        if self.save():
            self.cl_new.set("")
            self.refresh_checklist()

    def add_default_items(self):
        trip = self.cl_trip()
        if not trip:
            messagebox.showwarning("No trip selected", "Select a trip first.")
            return
        have = {i["text"].lower() for i in trip["checklist"]}
        new = [t for t in DEFAULT_PACKING if t.lower() not in have]
        if not new:
            messagebox.showinfo("Nothing to add", "All default suggestions are already on the list.")
            return
        trip["checklist"] += [{"text": t, "done": False} for t in new]
        if self.save():
            self.refresh_checklist()
            messagebox.showinfo("Added", f"{len(new)} suggested item(s) added.")

    def toggle_item(self, item, var):
        item["done"] = bool(var.get())
        self.save()
        self.after_idle(self.refresh_checklist)

    def delete_item(self, item):
        trip = self.cl_trip()
        if trip and item in trip["checklist"]:
            if not messagebox.askyesno("Confirm delete", f"Remove '{item['text']}' from the checklist?"):
                return
            trip["checklist"].remove(item)
            if self.save():
                self.after_idle(self.refresh_checklist)

    def refresh_checklist(self):
        for w in self.cl_inner.winfo_children():
            w.destroy()
        trip = self.cl_trip()
        if not trip:
            self.cl_bar["value"] = 0
            self.cl_stat.config(text="Select a trip to see its checklist")
            return
        items = trip["checklist"]
        done = sum(1 for i in items if i["done"])
        pct = round(done * 100 / len(items)) if items else 0
        self.cl_bar["value"] = pct
        self.cl_stat.config(text=f"{pct}% complete  |  Completed: {done}  |  Pending: {len(items) - done}")
        mode = self.cl_filter.get()
        shown = 0
        for item in items:
            if (mode == "Pending" and item["done"]) or (mode == "Completed" and not item["done"]):
                continue
            shown += 1
            row = tk.Frame(self.cl_inner, bg=WHITE)
            row.pack(fill="x", pady=2, padx=8)
            var = tk.BooleanVar(value=item["done"])
            cb = tk.Checkbutton(row, text=item["text"], variable=var, bg=WHITE,
                                activebackground=WHITE, font=(FONT, 11), anchor="w",
                                fg=MUTED if item["done"] else TEXT, selectcolor=WHITE,
                                command=lambda i=item, v=var: self.toggle_item(i, v))
            cb.pack(side="left")
            ttk.Button(row, text="Delete", style="Beige.TButton", width=8,
                       command=lambda i=item: self.delete_item(i)).pack(side="right")
        if shown == 0:
            msg = "No items yet. Add your own or use the default suggestions." if not items \
                else f"No {mode.lower()} items."
            tk.Label(self.cl_inner, text=msg, bg=WHITE, fg=MUTED, font=(FONT, 10)).pack(pady=20)

    # ---- B. memories
    def build_memories(self, tab):
        form = ttk.LabelFrame(tab, text="Record a Visit", padding=8)
        form.pack(fill="x")
        form.grid_columnconfigure(1, weight=1)
        ttk.Label(form, text="Destination *").grid(row=0, column=0, sticky="w", padx=(10, 6), pady=5)
        self.m_dest = ttk.Combobox(form, state="readonly", width=34)
        self.m_dest.grid(row=0, column=1, sticky="w", pady=5)
        self.m_date = tk.StringVar()
        ttk.Label(form, text="Travel Date (YYYY-MM-DD) *").grid(row=0, column=2, sticky="w", padx=(20, 6))
        ttk.Entry(form, textvariable=self.m_date, width=16).grid(row=0, column=3, sticky="w", padx=(0, 10))
        ttk.Label(form, text="Memory").grid(row=1, column=0, sticky="nw", padx=(10, 6), pady=5)
        self.m_text = tk.Text(form, height=4, width=70, font=(FONT, 10), wrap="word",
                              relief="solid", bd=1, highlightthickness=0)
        self.m_text.grid(row=1, column=1, columnspan=3, sticky="ew", pady=5, padx=(0, 10))
        row = ttk.Frame(form)
        row.grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 2))
        self.btn(row, "Mark Visited & Save Memory", self.save_memory).pack(side="left", padx=(0, 8))
        self.btn(row, "Remove Visited Mark", self.unmark_visited, "Accent.TButton").pack(side="left", padx=(0, 8))
        self.btn(row, "Clear", self.clear_memory_form, "Beige.TButton").pack(side="left")

        ttk.Label(tab, text="Places you have visited (select a row to view or edit its memory)",
                  style="Sub.TLabel").pack(anchor="w", pady=(12, 4))
        frame, self.mem_tree = self.make_tree(
            tab, ("Destination", "Country", "Travel Date", "Memory"), (170, 110, 100, 430), 7)
        frame.pack(fill="both", expand=True)
        self.mem_tree.bind("<<TreeviewSelect>>", self.on_memory_select)

    def save_memory(self):
        dest = self.dest_by_id(self.combo_id(self.m_dest))
        if not dest:
            messagebox.showerror("Missing information", "Please select a destination.")
            return
        try:
            day = parse_date(self.m_date.get())
        except ValueError:
            messagebox.showerror("Invalid date", "Enter the travel date as YYYY-MM-DD.")
            return
        if day > date.today():
            messagebox.showerror("Invalid date", "A visited trip cannot have a date in the future.")
            return
        dest["status"] = "Visited"
        dest["visit_date"] = day.strftime(DATE_FMT)
        dest["memory"] = self.m_text.get("1.0", "end").strip()[:1000]
        if self.save():
            self.refresh_all()
            messagebox.showinfo("Saved", f"{dest['name']} is marked as visited and your memory is saved.")

    def unmark_visited(self):
        dest = self.dest_by_id(self.combo_id(self.m_dest))
        if not dest:
            messagebox.showwarning("No selection", "Select a destination first.")
            return
        if dest["status"] != "Visited":
            messagebox.showinfo("Not visited", f"{dest['name']} is not marked as visited.")
            return
        if not messagebox.askyesno("Confirm", f"Remove the visited mark and memory for '{dest['name']}'?"):
            return
        dest.update({"status": "Wishlist", "visit_date": "", "memory": ""})
        if self.save():
            self.clear_memory_form()
            self.refresh_all()

    def clear_memory_form(self):
        self.m_dest.set("")
        self.m_date.set("")
        self.m_text.delete("1.0", "end")
        if hasattr(self, "mem_tree"):
            self.mem_tree.selection_set(())

    def on_memory_select(self, _event=None):
        sel = self.mem_tree.selection()
        if not sel:
            return
        dest = self.dest_by_id(int(sel[0]))
        if not dest:
            return
        ids = [d["id"] for d in self.d["destinations"]]
        self.m_dest.current(ids.index(dest["id"]))
        self.m_date.set(dest["visit_date"])
        self.m_text.delete("1.0", "end")
        self.m_text.insert("1.0", dest["memory"])

    def refresh_extras(self):
        self.refill_combo(self.cl_combo, self.d["trips"], self.trip_label)
        self.refresh_checklist()
        self.refill_combo(self.m_dest, self.d["destinations"], lambda d: f"{d['name']}, {d['country']}")
        self.mem_tree.delete(*self.mem_tree.get_children())
        visited = [d for d in self.d["destinations"] if d["status"] == "Visited"]
        for d in sorted(visited, key=lambda d: d["visit_date"], reverse=True):
            self.mem_tree.insert("", "end", iid=str(d["id"]),
                                 values=(d["name"], d["country"], d["visit_date"] or "Not set",
                                         shorten(d["memory"], 90) or "(no memory written)"))

    # ================================================================== refresh everything
    def refresh_all(self):
        if not hasattr(self, "pages") or len(self.pages) < len(self.PAGES):
            return
        self.refresh_dashboard()
        self.refresh_bucket()
        self.refresh_planner()
        self.refresh_budget()
        self.refresh_extras()


def main():
    try:  # sharper text on Windows high-DPI screens
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    WanderListApp().mainloop()


if __name__ == "__main__":
    main()
