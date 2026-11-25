from pathlib import Path


PAGE_WIDTH = 792
PAGE_HEIGHT = 612
MARGIN = 32
INK = (0.11, 0.16, 0.22)
MUTED = (0.36, 0.42, 0.48)
LINE = (0.84, 0.88, 0.92)
PANEL = (0.97, 0.98, 0.99)
BLUE = (0.18, 0.44, 0.93)
BLUE_FILL = (0.86, 0.91, 0.99)
GREEN = (0.18, 0.62, 0.36)
AMBER = (0.84, 0.53, 0.10)
RED = (0.85, 0.28, 0.37)


def _pdf_text(value):
    value = str(value).encode("ascii", "replace").decode("ascii")
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _color(color):
    return " ".join("%.3f" % component for component in color)


class PDFCanvas:
    def __init__(self):
        self.commands = []

    def text(self, x, y, value, size=8, color=INK, bold=False):
        font = "F2" if bold else "F1"
        self.commands.append(
            "BT /%s %s Tf %s rg 1 0 0 1 %.2f %.2f Tm (%s) Tj ET"
            % (font, size, _color(color), x, y, _pdf_text(value))
        )

    def line(self, x1, y1, x2, y2, color=LINE, width=0.7):
        self.commands.append(
            "%s RG %.2f w %.2f %.2f m %.2f %.2f l S"
            % (_color(color), width, x1, y1, x2, y2)
        )

    def rect(self, x, y, width, height, fill=None, stroke=LINE, line_width=0.7):
        command = []
        if fill is not None:
            command.append("%s rg" % _color(fill))
        command.extend(
            [
                "%s RG" % _color(stroke),
                "%.2f w" % line_width,
                "%.2f %.2f %.2f %.2f re" % (x, y, width, height),
                "B" if fill is not None else "S",
            ]
        )
        self.commands.append(" ".join(command))

    def filled_rect(self, x, y, width, height, fill):
        self.commands.append(
            "%s rg %.2f %.2f %.2f %.2f re f"
            % (_color(fill), x, y, width, height)
        )

    def diagram_fill(self, points, baseline):
        if not points:
            return
        path = ["%.2f %.2f m" % (points[0][0], baseline)]
        path.extend("%.2f %.2f l" % point for point in points)
        path.append("%.2f %.2f l h" % (points[-1][0], baseline))
        self.commands.append(
            "%s rg %s f" % (_color(BLUE_FILL), " ".join(path))
        )

    def diagram_line(self, points):
        if len(points) < 2:
            return
        path = ["%.2f %.2f m" % points[0]]
        path.extend("%.2f %.2f l" % point for point in points[1:])
        self.commands.append(
            "%s RG 1.35 w %s S" % (_color(BLUE), " ".join(path))
        )

    def stream(self):
        return "\n".join(self.commands).encode("ascii", "replace")


def _wrap(text, max_chars):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _load_descriptions(model):
    descriptions = []
    for load in model.point_loads:
        descriptions.append(
            "Point: %.3g k at %.3g ft" % (load.magnitude, load.position)
        )
    for load in model.uniform_loads:
        descriptions.append(
            "Uniform: %.3g k/ft from %.3g to %.3g ft"
            % (load.magnitude, load.start, load.end)
        )
    if not descriptions:
        return ["No applied loads"]
    return descriptions


def _add_header(canvas, page_title):
    canvas.text(MARGIN, 579, page_title, size=17, bold=True)
    canvas.text(
        PAGE_WIDTH - MARGIN - 52,
        581,
        "BEAM DESIGNER",
        size=8,
        color=MUTED,
        bold=True,
    )
    canvas.line(MARGIN, 568, PAGE_WIDTH - MARGIN, 568, color=BLUE, width=1.5)


def _add_inputs(canvas, model, load_lines):
    x = MARGIN
    y = 418
    width = PAGE_WIDTH - 2 * MARGIN
    height = 138
    canvas.rect(x, y, width, height, fill=PANEL)
    canvas.text(x + 12, y + height - 19, "BEAM INPUTS", size=9, bold=True)

    fields = [
        ("SUPPORT", "Simply supported" if model.support == "simply-supported" else "Cantilever"),
        ("SPAN", "%.2f ft" % model.span),
        ("MATERIAL / SECTION", "%s / %s" % (model.material, model.section)),
        ("DEFLECTION LIMIT", model.deflection_limit),
    ]
    col_width = (width - 24) / len(fields)
    for index, (label, value) in enumerate(fields):
        field_x = x + 12 + index * col_width
        canvas.text(field_x, y + 99, label, size=6.5, color=MUTED, bold=True)
        canvas.text(field_x, y + 84, value, size=8, bold=True)

    canvas.line(x + 12, y + 75, x + width - 12, y + 75, color=LINE)
    canvas.text(x + 12, y + 60, "LOADS (DOWNWARD POSITIVE)", size=6.5, color=MUTED, bold=True)
    load_y = y + 45
    visible_lines = load_lines[:2]
    for line in visible_lines:
        canvas.text(x + 12, load_y, line, size=7)
        load_y -= 12
    if len(load_lines) > 2:
        canvas.text(
            x + 12,
            load_y,
            "Additional load schedule on page 2",
            size=7,
            color=MUTED,
        )


def _add_load_schedule_page(canvas, model, descriptions, page_number, page_count):
    title = "BEAM INPUTS - LOAD SCHEDULE"
    if page_number > 1:
        title = "LOAD SCHEDULE - CONTINUED"
    _add_header(canvas, title)
    canvas.text(PAGE_WIDTH - MARGIN - 70, 22, "Schedule %d of %d" % (page_number, page_count), size=7, color=MUTED)
    canvas.text(MARGIN, 540, "Support:", size=9, color=MUTED)
    canvas.text(MARGIN + 58, 540, "Simply supported" if model.support == "simply-supported" else "Cantilever", size=9, bold=True)
    canvas.text(270, 540, "Span:", size=9, color=MUTED)
    canvas.text(304, 540, "%.2f ft" % model.span, size=9, bold=True)
    canvas.text(390, 540, "Material / section:", size=9, color=MUTED)
    canvas.text(485, 540, "%s / %s" % (model.material, model.section), size=9, bold=True)
    canvas.text(MARGIN, 514, "Deflection limit:", size=9, color=MUTED)
    canvas.text(112, 514, model.deflection_limit, size=9, bold=True)
    canvas.text(MARGIN, 482, "LOAD SCHEDULE", size=10, bold=True)
    canvas.line(MARGIN, 472, PAGE_WIDTH - MARGIN, 472, color=LINE)
    y = 454
    for index, description in enumerate(descriptions, start=1):
        canvas.text(MARGIN + 8, y, "%d." % index, size=8, color=MUTED)
        canvas.text(MARGIN + 34, y, description, size=8)
        y -= 18
        if y < 36:
            break


def _add_diagram(canvas, title, xs, values, span, panel_y, max_label, invert=False):
    panel_x = MARGIN
    panel_width = PAGE_WIDTH - 2 * MARGIN
    panel_height = 86
    canvas.rect(panel_x, panel_y, panel_width, panel_height, fill=(0.985, 0.989, 0.995))
    canvas.text(panel_x + 10, panel_y + 69, title, size=8, bold=True)
    canvas.text(
        panel_x + panel_width - 12 - len(max_label) * 3.7,
        panel_y + 69,
        max_label,
        size=7,
        color=MUTED,
    )

    plot_left = panel_x + 44
    plot_right = panel_x + panel_width - 16
    baseline = panel_y + 39
    plot_half_height = 20
    max_abs = max((abs(value) for value in values), default=0.0)
    if max_abs < 1e-12:
        max_abs = 1.0
    y_scale = plot_half_height / max_abs
    points = []
    for x_value, value in zip(xs, values):
        px = plot_left + (plot_right - plot_left) * x_value / span
        py_value = -value if invert else value
        py = baseline + py_value * y_scale
        points.append((px, py))

    canvas.line(plot_left, baseline, plot_right, baseline, color=(0.76, 0.81, 0.87), width=0.6)
    canvas.line(plot_left, panel_y + 14, plot_left, panel_y + 63, color=(0.87, 0.90, 0.94), width=0.5)
    canvas.diagram_fill(points, baseline)
    canvas.diagram_line(points)
    canvas.text(plot_left, panel_y + 5, "0 ft", size=6, color=MUTED)
    canvas.text(plot_right - 25, panel_y + 5, "%.2g ft" % span, size=6, color=MUTED)


def _add_check(canvas, x, y, width, title, actual, allowable, unit, passed):
    height = 82
    canvas.rect(x, y, width, height, fill=PANEL)
    color = GREEN if passed else RED
    canvas.text(x + 10, y + 65, title.upper(), size=8, bold=True)
    status_text = "PASS" if passed else "FAIL"
    canvas.filled_rect(x + width - 53, y + 59, 42, 15, (0.88, 0.96, 0.91) if passed else (0.99, 0.90, 0.92))
    canvas.text(x + width - 47, y + 63, status_text, size=7, color=color, bold=True)
    canvas.text(
        x + 10,
        y + 46,
        "Actual  %.3f %s     Allowable  %.3f %s"
        % (actual, unit, allowable, unit),
        size=7,
    )

    ratio = actual / allowable if allowable > 0 else 0
    bar_x = x + 10
    bar_y = y + 23
    bar_width = width - 20
    canvas.filled_rect(bar_x, bar_y, bar_width, 8, (0.91, 0.94, 0.97))
    ratio_color = GREEN if ratio < 0.70 else AMBER if ratio <= 1.0 else RED
    canvas.filled_rect(bar_x, bar_y, min(bar_width, bar_width * ratio), 8, ratio_color)
    canvas.text(x + 10, y + 8, "Utilization: %.1f%%" % (ratio * 100), size=6.5, color=MUTED)


def _page_streams(model, analysis):
    descriptions = _load_descriptions(model)
    load_lines = []
    for description in descriptions:
        load_lines.extend(_wrap(description, 118))
    if not load_lines:
        load_lines = ["No applied loads"]

    first_page = PDFCanvas()
    _add_header(first_page, "BEAM DESIGN CALCULATION SHEET")
    _add_inputs(first_page, model, load_lines)

    shear_label = "MAX SHEAR  %.3f k" % analysis.max_shear
    moment_label = "MAX MOMENT  %.3f kip-ft" % analysis.max_moment
    deflection_label = "MAX DEFLECTION  %.3f in" % analysis.max_deflection
    _add_diagram(first_page, "SHEAR DIAGRAM  |  kips", analysis.xs, analysis.shear, model.span, 318, shear_label)
    _add_diagram(first_page, "MOMENT DIAGRAM  |  kip-ft", analysis.xs, analysis.moment, model.span, 224, moment_label)
    _add_diagram(first_page, "DEFLECTION DIAGRAM  |  inches", analysis.xs, analysis.deflection, model.span, 130, deflection_label, invert=True)

    check_gap = 10
    check_width = (PAGE_WIDTH - 2 * MARGIN - check_gap) / 2
    _add_check(
        first_page,
        MARGIN,
        34,
        check_width,
        "Bending check",
        analysis.bending_stress,
        analysis.bending_allowable,
        "ksi",
        analysis.bending_pass,
    )
    _add_check(
        first_page,
        MARGIN + check_width + check_gap,
        34,
        check_width,
        "Deflection check",
        analysis.max_deflection,
        analysis.deflection_allowable,
        "in",
        analysis.deflection_pass,
    )

    pages = [first_page.stream()]
    if len(load_lines) > 2:
        all_load_descriptions = _load_descriptions(model)
        capacity = 23
        schedules = [
            all_load_descriptions[index:index + capacity]
            for index in range(0, len(all_load_descriptions), capacity)
        ]
        schedule_page_count = len(schedules)
        for page_number, descriptions in enumerate(schedules, start=1):
            schedule_page = PDFCanvas()
            _add_load_schedule_page(
                schedule_page,
                model,
                descriptions,
                page_number,
                schedule_page_count,
            )
            pages.append(schedule_page.stream())
    return pages


def _build_pdf(page_streams):
    page_count = len(page_streams)
    page_ids = list(range(3, 3 + page_count))
    content_ids = list(range(3 + page_count, 3 + 2 * page_count))
    regular_font_id = 3 + 2 * page_count
    bold_font_id = regular_font_id + 1

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            "<< /Type /Pages /Kids [%s] /Count %d >>"
            % (" ".join("%d 0 R" % page_id for page_id in page_ids), page_count)
        ).encode("ascii"),
    ]
    for page_id, content_id in zip(page_ids, content_ids):
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
                "/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> "
                "/Contents %d 0 R >>"
                % (PAGE_WIDTH, PAGE_HEIGHT, regular_font_id, bold_font_id, content_id)
            ).encode("ascii")
        )
    for stream in page_streams:
        objects.append(
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        )
    objects.extend(
        [
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        ]
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(("%d 0 obj\n" % object_id).encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(("xref\n0 %d\n" % (len(objects) + 1)).encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(("%010d 00000 n \n" % offset).encode("ascii"))
    pdf.extend(
        (
            "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objects) + 1, xref_offset)
        ).encode("ascii")
    )
    return pdf


def export_calculation_sheet(path, model, analysis):
    with Path(path).open("wb") as handle:
        handle.write(_build_pdf(_page_streams(model, analysis)))
