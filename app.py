import math
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from beam_calculations import (
    BeamModel,
    PointLoad,
    UniformLoad,
    calculate,
    sections_for,
)


BG = "#f4f7fb"
PANEL = "#ffffff"
PANEL_ALT = "#f8fafc"
LINE = "#dfe7f1"
TEXT = "#1d2a39"
MUTED = "#5c6b7a"
ACCENT = "#2f6fed"
ACCENT_SOFT = "#e9f0ff"
GREEN = "#2e9d5c"
AMBER = "#d6881b"
RED = "#d9485f"


PRESETS = {
    "Default: 20 ft Steel Floor Beam": {
        "support": "simply-supported",
        "span": 20,
        "material": "Steel",
        "section": "W12x26",
        "limit": "L/360",
        "points": [],
        "uniform": [(1.0, 0.0, 20.0)],
    },
    "12 ft Wood Deck Joist": {
        "support": "simply-supported",
        "span": 12,
        "material": "Douglas Fir-Larch",
        "section": "2x10",
        "limit": "L/360",
        "points": [],
        "uniform": [(0.05, 0.0, 12.0)],
    },
    "10 ft Steel Cantilever Canopy": {
        "support": "cantilever",
        "span": 10,
        "material": "Steel",
        "section": "W12x26",
        "limit": "L/360",
        "points": [(5.0, 10.0)],
        "uniform": [],
    },
    "30 ft Heavy Girder": {
        "support": "simply-supported",
        "span": 30,
        "material": "Steel",
        "section": "W24x55",
        "limit": "L/360",
        "points": [(20.0, 15.0)],
        "uniform": [(0.5, 0.0, 30.0)],
    },
}


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry("+%d+%d" % (x, y))
        tk.Label(
            self.tip,
            text=self.text,
            justify="left",
            background="#1d2a39",
            foreground="white",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
        ).pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class BeamDesignerApp:
    def __init__(self, root):
        self.root = root
        root.title("Beam Designer")
        root.geometry("1420x900")
        root.configure(background=BG)
        root.minsize(900, 650)

        self.model = BeamModel()
        self.model.point_loads = [PointLoad(1.0, 0.0)]
        self.model.uniform_loads = [UniformLoad(1.0, 0.0, 20.0)]
        self.point_loads = list(self.model.point_loads)
        self.uniform_loads = list(self.model.uniform_loads)

        self.drag_load_index = None
        self.crosshair_items = []
        self.redraw_after = None

        self.create_widgets()
        self.apply_preset("Default: 20 ft Steel Floor Beam")
        root.bind("<Configure>", lambda _event: self.schedule_redraw())

    def create_widgets(self):
        outer = tk.Frame(self.root, background=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        self.controls = tk.Frame(
            outer, background=PANEL, highlightbackground=LINE, highlightthickness=1
        )
        self.controls.pack(side="left", fill="y", ipadx=16, ipady=12)

        main = tk.Frame(outer, background=PANEL, highlightbackground=LINE, highlightthickness=1)
        main.pack(side="left", fill="both", expand=True, padx=(18, 0), ipadx=14, ipady=10)

        title = tk.Label(
            self.controls, text="BEAM SETTINGS", font=("TkDefaultFont", 11, "bold"),
            foreground=MUTED, background=PANEL,
        )
        title.pack(anchor="w", pady=(2, 12))

        self.preset_var = tk.StringVar(value="Default: 20 ft Steel Floor Beam")
        self.add_field_header(self.controls, "Load preset")
        preset = ttk.Combobox(
            self.controls, textvariable=self.preset_var, state="readonly",
            values=list(PRESETS.keys()),
        )
        preset.pack(fill="x", pady=(0, 12))
        preset.bind("<<ComboboxSelected>>", lambda _event: self.apply_preset(self.preset_var.get()))

        self.add_field_header(self.controls, "Support type")
        support_row = tk.Frame(self.controls, background=PANEL)
        support_row.pack(fill="x", pady=(0, 12))
        self.support_var = tk.StringVar(value="simply-supported")
        self.support_buttons = {}
        for key, label in (
            ("simply-supported", "Simply supported"),
            ("cantilever", "Cantilever"),
        ):
            button = tk.Radiobutton(
                support_row, text=label, variable=self.support_var, value=key,
                indicatoron=False, selectcolor=ACCENT_SOFT, background=PANEL,
                foreground=TEXT, activebackground=ACCENT_SOFT,
                relief="solid", borderwidth=1, padx=8, pady=7,
                command=self.on_model_change,
            )
            button.pack(side="left", fill="x", expand=True)
            self.support_buttons[key] = button

        self.add_field_header(self.controls, "Span", "ft")
        span_row = tk.Frame(self.controls, background=PANEL)
        span_row.pack(fill="x", pady=(0, 12))
        self.span_var = tk.DoubleVar(value=20)
        self.span_scale = ttk.Scale(
            span_row, from_=4, to=40, orient="horizontal",
            variable=self.span_var, command=self.on_span_scale,
        )
        self.span_scale.pack(side="left", fill="x", expand=True)
        self.span_entry = ttk.Entry(span_row, width=8)
        self.span_entry.insert(0, "20")
        self.span_entry.pack(side="left", padx=(10, 0))
        self.span_entry.bind("<FocusOut>", self.on_span_entry)
        self.span_entry.bind("<Return>", self.on_span_entry)

        self.add_field_header(self.controls, "Loads")
        self.load_list = tk.Frame(self.controls, background=PANEL)
        self.load_list.pack(fill="x", pady=(0, 8))
        load_buttons = tk.Frame(self.controls, background=PANEL)
        load_buttons.pack(fill="x", pady=(0, 12))
        ttk.Button(load_buttons, text="Add point load", command=self.add_point_load).pack(
            side="left", fill="x", expand=True, padx=(0, 4)
        )
        ttk.Button(load_buttons, text="Add uniform load", command=self.add_uniform_load).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )

        self.add_field_header(self.controls, "Material")
        material_row = tk.Frame(self.controls, background=PANEL)
        material_row.pack(fill="x", pady=(0, 12))
        self.material_var = tk.StringVar(value="Steel")
        self.section_var = tk.StringVar(value="W12x26")
        ttk.Label(material_row, text="Material").grid(row=0, column=0, sticky="w")
        ttk.Label(material_row, text="Section").grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.material_combo = ttk.Combobox(
            material_row, textvariable=self.material_var, state="readonly",
            values=["Steel", "Douglas Fir-Larch"], width=14,
        )
        self.material_combo.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.section_combo = ttk.Combobox(
            material_row, textvariable=self.section_var, state="readonly", width=12,
        )
        self.section_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        material_row.columnconfigure(0, weight=1)
        material_row.columnconfigure(1, weight=1)
        self.material_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_material_change())
        self.section_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_model_change())

        self.add_field_header(self.controls, "Deflection limit")
        self.limit_var = tk.StringVar(value="L/360")
        limit = ttk.Combobox(
            self.controls, textvariable=self.limit_var, state="readonly",
            values=["L/360", "L/240"],
        )
        limit.pack(fill="x")
        limit.bind("<<ComboboxSelected>>", lambda _event: self.on_model_change())

        header = tk.Frame(main, background=PANEL)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(
            header, text="BEAM REVIEW", font=("TkDefaultFont", 11, "bold"),
            foreground=MUTED, background=PANEL,
        ).pack(side="left")
        ttk.Button(
            header, text="Print / Save PDF Report", command=self.open_report
        ).pack(side="right")
        ttk.Button(
            header, text="Use suggested section", command=self.use_suggested
        ).pack(side="right", padx=(0, 8))

        self.suggestion_text = tk.StringVar(value="Suggested: W12x26")
        suggestion = tk.Frame(
            main, background="#f7f9ff", highlightbackground=LINE, highlightthickness=1
        )
        suggestion.pack(fill="x", pady=(0, 10), ipady=8)
        tk.Label(
            suggestion, textvariable=self.suggestion_text, foreground=TEXT,
            background="#f7f9ff", font=("TkDefaultFont", 12, "bold"),
        ).pack(anchor="w", padx=12)

        self.beam_canvas = tk.Canvas(
            main, height=150, background=PANEL_ALT, highlightthickness=1,
            highlightbackground=LINE,
        )
        self.beam_canvas.pack(fill="x", pady=(0, 8))
        self.beam_canvas.bind("<Motion>", self.on_canvas_drag)
        self.beam_canvas.bind("<ButtonRelease-1>", self.stop_drag)

        self.diagram_frame = tk.Frame(main, background=PANEL)
        self.diagram_frame.pack(fill="both", expand=True)
        self.diagram_canvases = []
        for title in ("Shear (kips)", "Moment (kip-ft)", "Deflected shape (in)"):
            frame = tk.Frame(
                self.diagram_frame, background=PANEL_ALT,
                highlightbackground=LINE, highlightthickness=1,
            )
            frame.pack(fill="x", pady=(0, 6))
            tk.Label(
                frame, text=title, foreground=MUTED, background=PANEL_ALT,
                font=("TkDefaultFont", 10, "bold"),
            ).pack(anchor="w", padx=8, pady=(5, 0))
            canvas = tk.Canvas(frame, height=92, background=PANEL_ALT, highlightthickness=0)
            canvas.pack(fill="x", padx=8, pady=(2, 5))
            canvas.bind("<Motion>", self.on_crosshair)
            canvas.bind("<Leave>", self.clear_crosshair)
            self.diagram_canvases.append(canvas)

        checks = tk.Frame(main, background=PANEL)
        checks.pack(fill="x", pady=(8, 0))
        checks.columnconfigure(0, weight=1)
        checks.columnconfigure(1, weight=1)
        self.bending_card = tk.Frame(
            checks, background=PANEL_ALT, highlightbackground=LINE, highlightthickness=1
        )
        self.bending_card.grid(row=0, column=0, sticky="ew", padx=(0, 6), ipady=8)
        self.deflection_card = tk.Frame(
            checks, background=PANEL_ALT, highlightbackground=LINE, highlightthickness=1
        )
        self.deflection_card.grid(row=0, column=1, sticky="ew", padx=(6, 0), ipady=8)
        self.build_check_card(self.bending_card, "Bending")
        self.build_check_card(self.deflection_card, "Deflection")

    def add_field_header(self, parent, label, unit=None):
        frame = tk.Frame(parent, background=PANEL)
        frame.pack(fill="x", pady=(0, 6))
        tk.Label(
            frame, text=label, foreground=TEXT, background=PANEL,
            font=("TkDefaultFont", 10, "bold"),
        ).pack(side="left")
        if unit:
            tk.Label(
                frame, text=unit, foreground=MUTED, background=PANEL,
                font=("TkDefaultFont", 9),
            ).pack(side="right")

    def build_check_card(self, card, name):
        for child in card.winfo_children():
            child.destroy()
        top = tk.Frame(card, background=PANEL_ALT)
        top.pack(fill="x", padx=12)
        tk.Label(
            top, text=name, background=PANEL_ALT, foreground=TEXT,
            font=("TkDefaultFont", 12, "bold"),
        ).pack(side="left")
        badge = tk.Label(
            top, text="PASS", background="#dff3e8", foreground=GREEN,
            font=("TkDefaultFont", 9, "bold"), padx=8, pady=3,
        )
        badge.pack(side="right")
        metrics = tk.Label(
            card, text="", justify="left", background=PANEL_ALT, foreground=TEXT,
        )
        metrics.pack(fill="x", padx=12, pady=(6, 4))
        track = tk.Canvas(card, height=10, background=PANEL_ALT, highlightthickness=0)
        track.pack(fill="x", padx=12)
        card.badge = badge
        card.metrics = metrics
        card.track = track
        formula = (
            "fb = |Mmax| x 12 / Sx"
            if name == "Bending"
            else "Deflection limit = span / 240 or 360"
        )
        ToolTip(card, formula)

    def rebuild_load_ui(self):
        for child in self.load_list.winfo_children():
            child.destroy()

        for index, load in enumerate(self.point_loads):
            card = tk.Frame(
                self.load_list, background=PANEL_ALT,
                highlightbackground=LINE, highlightthickness=1,
            )
            card.pack(fill="x", pady=(0, 6), padx=1)
            top = tk.Frame(card, background=PANEL_ALT)
            top.pack(fill="x", padx=6, pady=(5, 2))
            tk.Label(
                top, text="Point load", foreground=TEXT, background=PANEL_ALT,
                font=("TkDefaultFont", 9, "bold"),
            ).pack(side="left")
            ttk.Button(
                top, text="Remove", width=8,
                command=lambda i=index: self.remove_point_load(i),
            ).pack(side="right")
            fields = tk.Frame(card, background=PANEL_ALT)
            fields.pack(fill="x", padx=6, pady=(0, 6))
            mag = tk.StringVar(value=str(load.magnitude))
            pos = tk.StringVar(value=str(load.position))
            self.make_load_entry(fields, "kips", mag, 0,
                                 lambda *args, i=index, v=mag: self.update_point(i, "magnitude", v))
            self.make_load_entry(fields, "position ft", pos, 1,
                                 lambda *args, i=index, v=pos: self.update_point(i, "position", v))

        for index, load in enumerate(self.uniform_loads):
            card = tk.Frame(
                self.load_list, background=PANEL_ALT,
                highlightbackground=LINE, highlightthickness=1,
            )
            card.pack(fill="x", pady=(0, 6), padx=1)
            top = tk.Frame(card, background=PANEL_ALT)
            top.pack(fill="x", padx=6, pady=(5, 2))
            tk.Label(
                top, text="Uniform load", foreground=TEXT, background=PANEL_ALT,
                font=("TkDefaultFont", 9, "bold"),
            ).pack(side="left")
            ttk.Button(
                top, text="Remove", width=8,
                command=lambda i=index: self.remove_uniform_load(i),
            ).pack(side="right")
            fields = tk.Frame(card, background=PANEL_ALT)
            fields.pack(fill="x", padx=6, pady=(0, 6))
            mag = tk.StringVar(value=str(load.magnitude))
            start = tk.StringVar(value=str(load.start))
            end = tk.StringVar(value=str(load.end))
            self.make_load_entry(fields, "k/ft", mag, 0,
                                 lambda *args, i=index, v=mag: self.update_uniform(i, "magnitude", v))
            self.make_load_entry(fields, "start", start, 1,
                                 lambda *args, i=index, v=start: self.update_uniform(i, "start", v))
            self.make_load_entry(fields, "end", end, 2,
                                 lambda *args, i=index, v=end: self.update_uniform(i, "end", v))

    def make_load_entry(self, parent, label, variable, column, callback):
        frame = tk.Frame(parent, background=PANEL_ALT)
        frame.grid(row=0, column=column, sticky="ew", padx=(0, 5))
        parent.columnconfigure(column, weight=1)
        tk.Label(
            frame, text=label, foreground=MUTED, background=PANEL_ALT,
            font=("TkDefaultFont", 8),
        ).pack(anchor="w")
        entry = ttk.Entry(frame, textvariable=variable, width=8)
        entry.pack(fill="x")
        variable.trace_add("write", callback)

    def apply_preset(self, name):
        preset = PRESETS[name]
        self.support_var.set(preset["support"])
        self.span_var.set(preset["span"])
        self.span_entry.delete(0, "end")
        self.span_entry.insert(0, str(preset["span"]))
        self.material_var.set(preset["material"])
        self.limit_var.set(preset["limit"])
        self.point_loads = [PointLoad(mag, pos) for mag, pos in preset["points"]]
        self.uniform_loads = [UniformLoad(mag, start, end) for mag, start, end in preset["uniform"]]
        self.update_section_options(preset["section"])
        self.rebuild_load_ui()
        self.on_model_change()

    def update_section_options(self, selected=None):
        names = [section["name"] for section in sections_for(self.material_var.get())]
        self.section_combo.configure(values=names)
        if selected in names:
            self.section_var.set(selected)
        else:
            self.section_var.set(names[0])

    def on_material_change(self):
        names = [section["name"] for section in sections_for(self.material_var.get())]
        self.section_combo.configure(values=names)
        self.section_var.set(names[0])
        self.on_model_change()

    def on_span_scale(self, value):
        span = round(float(value), 1)
        self.span_entry.delete(0, "end")
        self.span_entry.insert(0, str(span))
        self.on_model_change()

    def on_span_entry(self, _event=None):
        try:
            span = float(self.span_entry.get())
        except ValueError:
            span = self.span_var.get()
        span = max(4.0, min(40.0, span))
        span = round(span, 2)
        self.span_var.set(span)
        self.span_entry.delete(0, "end")
        self.span_entry.insert(0, str(span))
        self.on_model_change()

    def add_point_load(self):
        span = float(self.span_var.get())
        position = span / 2 if self.support_var.get() == "simply-supported" else span
        self.point_loads.append(PointLoad(1.0, position))
        self.rebuild_load_ui()
        self.on_model_change()

    def add_uniform_load(self):
        span = float(self.span_var.get())
        self.uniform_loads.append(UniformLoad(0.1, 0.0, span))
        self.rebuild_load_ui()
        self.on_model_change()

    def remove_point_load(self, index):
        del self.point_loads[index]
        self.rebuild_load_ui()
        self.on_model_change()

    def remove_uniform_load(self, index):
        del self.uniform_loads[index]
        self.rebuild_load_ui()
        self.on_model_change()

    def update_point(self, index, field, variable):
        try:
            value = float(variable.get())
            if field == "position":
                value = max(0.0, min(float(self.span_var.get()), value))
            setattr(self.point_loads[index], field, value)
            self.on_model_change()
        except (ValueError, IndexError):
            pass

    def update_uniform(self, index, field, variable):
        try:
            value = float(variable.get())
            setattr(self.uniform_loads[index], field, value)
            self.on_model_change()
        except (ValueError, IndexError):
            pass

    def current_model(self):
        point_loads = [
            PointLoad(max(0.0, load.magnitude), min(max(load.position, 0.0), float(self.span_var.get())))
            for load in self.point_loads
        ]
        uniform_loads = [
            UniformLoad(
                max(0.0, load.magnitude),
                min(max(load.start, 0.0), float(self.span_var.get())),
                min(max(load.end, 0.0), float(self.span_var.get())),
            )
            for load in self.uniform_loads
        ]
        return BeamModel(
            preset=self.preset_var.get(),
            support=self.support_var.get(),
            span=float(self.span_var.get()),
            material=self.material_var.get(),
            section=self.section_var.get(),
            deflection_limit=self.limit_var.get(),
            point_loads=point_loads,
            uniform_loads=uniform_loads,
        )

    def on_model_change(self, _event=None):
        self.model = self.current_model()
        self.schedule_redraw()

    def schedule_redraw(self):
        if self.redraw_after:
            self.root.after_cancel(self.redraw_after)
        self.redraw_after = self.root.after(30, self.redraw)

    def redraw(self):
        self.redraw_after = None
        try:
            analysis = calculate(self.model)
        except Exception as exc:
            messagebox.showerror("Calculation error", str(exc))
            return
        self.analysis = analysis
        self.suggestion_text.set(
            "Current section: %s    |    Lightest passing: %s"
            % (self.model.section, analysis.suggested_section)
        )
        self.draw_beam(analysis)
        self.draw_diagram(0, analysis.xs, analysis.shear, "k",
                         "Vmax = %.2f k" % analysis.max_shear,
                         analysis.max_shear_x)
        self.draw_diagram(1, analysis.xs, analysis.moment, "kip-ft",
                         "Mmax = %.2f kip-ft" % analysis.max_moment,
                         analysis.max_moment_x)
        self.draw_diagram(2, analysis.xs, analysis.deflection, "in",
                         "ymax = %.3f in" % analysis.max_deflection,
                         analysis.max_deflection_x)
        self.update_check_card(
            self.bending_card, analysis.bending_stress, analysis.bending_allowable,
            analysis.bending_pass, "ksi",
        )
        self.update_check_card(
            self.deflection_card, analysis.max_deflection,
            analysis.deflection_allowable, analysis.deflection_pass, "in",
        )

    def update_check_card(self, card, actual, allowable, passed, unit):
        card.badge.configure(
            text="PASS" if passed else "FAIL",
            background="#dff3e8" if passed else "#fce7eb",
            foreground=GREEN if passed else RED,
        )
        card.metrics.configure(
            text="Actual: %.3f %s\nAllowable: %.3f %s" % (
                actual, unit, allowable, unit
            )
        )
        ratio = actual / allowable if allowable else 1.0
        card.track.delete("all")
        width = card.track.winfo_width() or 300
        card.track.create_rectangle(0, 0, width, 10, fill="#edf2f9", outline="")
        color = GREEN if ratio < 0.70 else AMBER if ratio <= 1.0 else RED
        fill_width = min(width, max(2, width * ratio))
        card.track.create_rectangle(0, 0, fill_width, 10, fill=color, outline="")

    def beam_geometry(self, canvas):
        width = canvas.winfo_width()
        left = 70
        right = max(left + 100, width - 70)
        y = 72
        return left, right, y

    def draw_beam(self, analysis):
        canvas = self.beam_canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        if width < 100:
            return
        left, right, y = self.beam_geometry(canvas)
        span = self.model.span
        scale = (right - left) / span

        canvas.create_line(left, y, right, y, fill=TEXT, width=8)
        canvas.create_line(left, y + 4, right, y + 4, fill="#8ca0b8", width=2)

        if self.model.support == "cantilever":
            canvas.create_rectangle(left - 18, y - 28, left - 5, y + 28,
                                    fill="#cfd8e5", outline="#7d8ea4")
            for offset in range(-18, 30, 8):
                canvas.create_line(left - 18 + offset, y + 28,
                                   left - 10 + offset, y + 36,
                                   fill="#7d8ea4")
        else:
            for x in (left, right):
                canvas.create_polygon(x - 12, y + 8, x + 12, y + 8, x, y + 32,
                                      fill="#cfd8e5", outline="#7d8ea4")
                canvas.create_line(x - 16, y + 32, x + 16, y + 32, fill="#7d8ea4")

        for index, load in enumerate(self.model.point_loads):
            x = left + load.position * scale
            magnitude = max(0.1, load.magnitude)
            length = min(42, 18 + magnitude * 3)
            canvas.create_line(x, y - length - 8, x, y - 8,
                               fill=ACCENT, width=2, arrow="last", tags=("point-load", str(index)))
            canvas.create_text(x, y - length - 16, text="%.2f k" % load.magnitude,
                               fill=TEXT, font=("TkDefaultFont", 9, "bold"))

        for load in self.model.uniform_loads:
            start = left + min(max(load.start, 0), span) * scale
            end = left + min(max(load.end, 0), span) * scale
            count = max(2, int((end - start) / 24))
            for i in range(count + 1):
                x = start + (end - start) * i / count
                canvas.create_line(x, y - 48, x, y - 8,
                                   fill=ACCENT, width=1, arrow="last")
            canvas.create_text((start + end) / 2, y - 58,
                               text="%.2f k/ft" % load.magnitude,
                               fill=TEXT, font=("TkDefaultFont", 9, "bold"))

        if self.model.support == "cantilever":
            canvas.create_text(left + 20, y + 44,
                               text="R = %.2f k" % abs(analysis.reactions[0]),
                               fill=MUTED, font=("TkDefaultFont", 9))
            canvas.create_text(left + 118, y + 44,
                               text="Mfixed = %.2f kip-ft" % abs(analysis.reactions[1]),
                               fill=MUTED, font=("TkDefaultFont", 9))
        else:
            canvas.create_text(left, y + 44,
                               text="RA = %.2f k" % analysis.reactions[0],
                               fill=MUTED, font=("TkDefaultFont", 9))
            canvas.create_text(right, y + 44,
                               text="RB = %.2f k" % analysis.reactions[1],
                               fill=MUTED, font=("TkDefaultFont", 9))

        canvas.create_text((left + right) / 2, y + 58,
                           text="%.1f ft span" % span, fill=MUTED,
                           font=("TkDefaultFont", 9))

    def on_canvas_drag(self, event):
        if event.type == tk.EventType.ButtonPress:
            pass
        if event.state & 0x100:
            if self.drag_load_index is not None:
                left, right, _ = self.beam_geometry(self.beam_canvas)
                span = self.model.span
                position = (event.x - left) / ((right - left) / span)
                position = max(0.0, min(span, position))
                position = round(position * 4) / 4
                self.point_loads[self.drag_load_index].position = position
                self.rebuild_load_ui()
                self.on_model_change()
                return
        item = self.beam_canvas.find_withtag("current")
        if item:
            tags = self.beam_canvas.gettags(item[0])
            if "point-load" in tags:
                for tag in tags:
                    if tag.isdigit():
                        self.drag_load_index = int(tag)

    def stop_drag(self, _event):
        self.drag_load_index = None

    def draw_diagram(self, index, xs, values, unit, label, max_x):
        canvas = self.diagram_canvases[index]
        canvas.delete("all")
        width = canvas.winfo_width()
        if width < 100:
            width = 800
        height = canvas.winfo_height() or 92
        left, right = 40, width - 20
        top, bottom = 12, height - 24
        baseline = bottom
        span = self.model.span
        x_scale = (right - left) / span

        max_abs = max((abs(value) for value in values), default=1.0)
        if max_abs < 1e-9:
            max_abs = 1.0
        y_scale = (bottom - top) * 0.42 / max_abs

        canvas.create_line(left, baseline, right, baseline, fill="#cad5e3", width=1)
        canvas.create_line(left, top, left, bottom, fill="#cad5e3", width=1)

        points = []
        for x, value in zip(xs, values):
            px = left + x * x_scale
            py = baseline - value * y_scale
            points.extend((px, py))
        if len(points) >= 4:
            fill_points = [left, baseline] + points + [right, baseline]
            canvas.create_polygon(fill_points, fill="#dde7fb", outline="")
            canvas.create_line(points, fill=ACCENT, width=2, smooth=True)

        px = left + max_x * x_scale
        canvas.create_text(
            min(right - 30, max(left + 30, px)),
            8,
            text=label,
            fill=TEXT,
            font=("TkDefaultFont", 9, "bold"),
            anchor="n",
        )
        canvas.create_text(left + (right - left) / 2, height - 8,
                           text="x = %.2f ft" % max_x, fill=MUTED,
                           font=("TkDefaultFont", 8))

    def on_crosshair(self, event):
        canvas = event.widget
        left, right = 40, canvas.winfo_width() - 20
        x_ft = max(0.0, min(self.model.span,
                            (event.x - left) / ((right - left) / self.model.span)))
        for cross_canvas in self.diagram_canvases:
            cross_canvas.delete("crosshair")
            px = left + x_ft * (cross_canvas.winfo_width() - left - 20) / self.model.span
            cross_canvas.create_line(
                px, 8, px, (cross_canvas.winfo_height() or 92) - 20,
                fill="#7d8ea4", dash=(4, 3), tags="crosshair",
            )

        shear = self.interpolate(self.analysis.xs, self.analysis.shear, x_ft)
        moment = self.interpolate(self.analysis.xs, self.analysis.moment, x_ft)
        deflection = self.interpolate(self.analysis.xs, self.analysis.deflection, x_ft)
        text = "x %.2f ft\nV %.2f k\nM %.2f kip-ft\ny %.3f in" % (
            x_ft, shear, moment, deflection,
        )
        canvas.create_text(
            min(right - 55, max(left + 55, event.x)),
            28,
            text=text,
            fill=TEXT,
            justify="left",
            font=("TkDefaultFont", 8, "bold"),
            tags="crosshair",
        )

    def clear_crosshair(self, _event):
        for canvas in self.diagram_canvases:
            canvas.delete("crosshair")

    def interpolate(self, xs, values, x):
        if x <= xs[0]:
            return values[0]
        if x >= xs[-1]:
            return values[-1]
        for i in range(len(xs) - 1):
            if xs[i] <= x <= xs[i + 1]:
                fraction = (x - xs[i]) / (xs[i + 1] - xs[i])
                return values[i] + fraction * (values[i + 1] - values[i])
        return values[-1]

    def use_suggested(self):
        self.section_var.set(self.analysis.suggested_section)
        self.on_model_change()

    def open_report(self):
        if not hasattr(self, "analysis"):
            return
        report = tk.Toplevel(self.root)
        report.title("Beam Summary Report")
        report.geometry("620x520")
        report.configure(background=PANEL)

        tk.Label(
            report, text="Beam summary report",
            font=("TkDefaultFont", 16, "bold"), background=PANEL, foreground=TEXT,
        ).pack(anchor="w", padx=20, pady=(18, 12))

        a = self.analysis
        if self.model.support == "cantilever":
            reaction_text = "R = %.2f k; Mfixed = %.2f kip-ft" % (
                abs(a.reactions[0]), abs(a.reactions[1])
            )
        else:
            reaction_text = "RA = %.2f k; RB = %.2f k" % (
                a.reactions[0], a.reactions[1]
            )
        lines = [
            ("Preset", self.model.preset),
            ("Support", "Simply supported" if self.model.support == "simply-supported" else "Cantilever"),
            ("Span", "%.2f ft" % self.model.span),
            ("Material", self.model.material),
            ("Section", self.model.section),
            ("Deflection limit", self.model.deflection_limit),
            ("Reactions", reaction_text),
            ("Maximum shear", "%.2f k" % a.max_shear),
            ("Maximum moment", "%.2f kip-ft" % a.max_moment),
            ("Maximum deflection", "%.3f in" % a.max_deflection),
            ("Bending", "PASS" if a.bending_pass else "FAIL"),
            ("Deflection", "PASS" if a.deflection_pass else "FAIL"),
        ]

        grid = tk.Frame(report, background=PANEL)
        grid.pack(fill="both", expand=True, padx=20)
        for index, (label, value) in enumerate(lines):
            row = index // 2
            col = index % 2
            frame = tk.Frame(grid, background=PANEL_ALT,
                             highlightbackground=LINE, highlightthickness=1)
            frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5, ipadx=8, ipady=8)
            grid.columnconfigure(col, weight=1)
            tk.Label(frame, text=label.upper(), foreground=MUTED, background=PANEL_ALT,
                     font=("TkDefaultFont", 8, "bold")).pack(anchor="w")
            tk.Label(frame, text=value, foreground=TEXT, background=PANEL_ALT,
                     font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(4, 0))

        actions = tk.Frame(report, background=PANEL)
        actions.pack(fill="x", padx=20, pady=12)
        ttk.Button(actions, text="Save Report",
                   command=lambda: self.save_report(lines)).pack(side="left")
        ttk.Button(actions, text="Print",
                   command=lambda: self.print_report(report, lines)).pack(side="left", padx=8)

    def save_report(self, lines):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text report", "*.txt"), ("PDF report", "*.pdf"), ("All files", "*.*")],
            title="Save Beam Report",
        )
        if not path:
            return
        content = "BEAM SUMMARY REPORT\n\n" + "\n".join(
            "%s: %s" % (label, value) for label, value in lines
        ) + "\n"
        if path.lower().endswith(".pdf"):
            try:
                self.write_simple_pdf(path, content)
            except Exception as exc:
                messagebox.showerror("PDF save failed", str(exc))
                return
        else:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
        messagebox.showinfo("Report saved", path)

    def write_simple_pdf(self, path, content):
        lines = content.splitlines()
        escaped = []
        for line in lines:
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            escaped.append(safe)
        stream_lines = ["BT", "/F1 11 Tf", "50 760 Td", "16 TL"]
        for index, line in enumerate(escaped):
            stream_lines.append("(%s) Tj" % line)
            if index != len(escaped) - 1:
                stream_lines.append("T*")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode("latin-1", "replace")

        objects = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        )
        objects.append(
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        )
        objects.append(
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        )

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(("%d 0 obj\n" % index).encode("ascii"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")
        xref = len(pdf)
        pdf.extend(("xref\n0 %d\n" % (len(objects) + 1)).encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(("%010d 00000 n \n" % offset).encode("ascii"))
        pdf.extend(
            ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
             % (len(objects) + 1, xref)).encode("ascii")
        )
        with open(path, "wb") as handle:
            handle.write(pdf)

    def print_report(self, window, lines):
        ps_path = os.path.join(os.path.dirname(__file__), "beam_report.ps")
        try:
            window.update()
            window.postscript(file=ps_path, colormode="color")
            if os.name == "nt":
                os.startfile(ps_path, "print")
            else:
                os.system("lpr %s" % ps_path)
            messagebox.showinfo("Print submitted", "The report was sent to the default printer.")
        except Exception as exc:
            messagebox.showerror("Print failed", str(exc))


def main():
    root = tk.Tk()
    BeamDesignerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
