"""
formatter.py
Renders a parsed reinstatement-report JSON dict into a polished PDF
using ReportLab Platypus.
"""

import html
import re

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.platypus import HRFlowable
from reportlab.platypus.flowables import Flowable

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
NAVY = colors.HexColor("#1B2A4A")
TEAL = colors.HexColor("#1A7F7A")
TEAL_LIGHT = colors.HexColor("#E8F5F4")
GOLD = colors.HexColor("#C8922A")
GREY_DARK = colors.HexColor("#2D3748")
GREY_MID = colors.HexColor("#718096")
GREY_LIGHT = colors.HexColor("#F7FAFC")
GREY_LINE = colors.HexColor("#CBD5E0")
WHITE = colors.white
RED_SOFT = colors.HexColor("#FFF5F5")
RED_BORDER = colors.HexColor("#FC8181")
GREEN_SOFT = colors.HexColor("#F0FFF4")
GREEN_BDR = colors.HexColor("#68D391")

PAGE_W = 7.0 * inch  # usable width (0.75" margins each side on letter)
DEFAULT_TEXT = "-"


def _text(value, default: str = DEFAULT_TEXT) -> str:
    if value is None:
        return default

    text = str(value).strip()
    if not text:
        return default

    if chr(0x00E2) in text or chr(0x00C3) in text:
        try:
            decoded = text.encode("latin1").decode("utf-8")
            if "\ufffd" not in decoded:
                text = decoded
        except UnicodeError:
            pass

    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\ufffd": '"',
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def _inline_text(value, default: str = DEFAULT_TEXT) -> str:
    """Escape user/model text and translate simple markdown into ReportLab tags."""
    text = html.escape(_text(value, default), quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    text = re.sub(r"`([^`\n]+?)`", r'<font name="Courier">\1</font>', text)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!_)_(?!_)([^_\n]+?)(?<!_)_(?!_)", r"<i>\1</i>", text)
    return text.replace("\n", "<br/>")


def _para(value, style, default: str = DEFAULT_TEXT) -> Paragraph:
    return Paragraph(_inline_text(value, default), style)


def _strip_list_marker(value: str) -> str:
    return re.sub(r"^\s*(?:[-*\u2022]+|\d+[.)])\s+", "", value).strip()


# ---------------------------------------------------------------------------
# Custom flowable: coloured left-bar callout box
# ---------------------------------------------------------------------------
class CalloutBox(Flowable):
    def __init__(self, paragraphs, bar_color=TEAL, bg_color=TEAL_LIGHT, width=PAGE_W):
        super().__init__()
        self._paras = paragraphs
        self._bar = bar_color
        self._bg = bg_color
        self._width = width
        self._inner_w = width - 0.18 * inch - 0.3 * inch  # bar + right pad
        # Measure height
        self._height = 0.18 * inch  # top pad
        for p in paragraphs:
            w, h = p.wrap(self._inner_w, 9999)
            self._height += h + 4
        self._height += 0.14 * inch  # bottom pad

    def wrap(self, availW, availH):
        return self._width, self._height

    def split(self, availW, availH):
        if self._height <= availH:
            return [self]

        top_pad = 0.18 * inch
        bottom_pad = 0.14 * inch
        line_gap = 4
        max_height = max(availH, top_pad + bottom_pad + 1)

        if len(self._paras) == 1:
            paragraph = self._paras[0]
            paragraph_parts = paragraph.split(self._inner_w, max_height - top_pad - bottom_pad)
            if paragraph_parts and len(paragraph_parts) > 1:
                return [
                    CalloutBox([part], bar_color=self._bar, bg_color=self._bg, width=self._width)
                    for part in paragraph_parts
                ]
            return [paragraph]

        chunks = []
        current = []
        current_height = top_pad + bottom_pad

        for paragraph in self._paras:
            _, paragraph_height = paragraph.wrap(self._inner_w, 9999)
            next_height = current_height + paragraph_height + (line_gap if current else 0)

            if current and next_height > max_height:
                chunks.append(CalloutBox(current, bar_color=self._bar, bg_color=self._bg, width=self._width))
                current = [paragraph]
                current_height = top_pad + bottom_pad + paragraph_height
                continue

            current.append(paragraph)
            current_height = next_height

        if current:
            chunks.append(CalloutBox(current, bar_color=self._bar, bg_color=self._bg, width=self._width))

        return chunks

    def draw(self):
        c = self.canv
        h = self._height
        w = self._width
        # Background
        c.setFillColor(self._bg)
        c.roundRect(0, 0, w, h, 4, stroke=0, fill=1)
        # Left accent bar
        c.setFillColor(self._bar)
        c.rect(0, 0, 4, h, stroke=0, fill=1)
        # Draw paragraphs
        x = 0.18 * inch
        y = h - 0.18 * inch
        for p in self._paras:
            pw, ph = p.wrap(self._inner_w, 9999)
            y -= ph
            p.drawOn(c, x, y)
            y -= 4
        c.setFillColor(colors.black)


# ---------------------------------------------------------------------------
# Style factory
# ---------------------------------------------------------------------------
def _styles():
    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "cover_title": ps(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=WHITE,
            leading=28,
            alignment=1,
            spaceAfter=6,
        ),
        "cover_sub": ps(
            "cover_sub",
            fontName="Helvetica",
            fontSize=11,
            textColor=colors.HexColor("#B2C8D8"),
            alignment=1,
            spaceAfter=0,
        ),
        "section_heading": ps(
            "section_heading",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=NAVY,
            leading=16,
            spaceBefore=18,
            spaceAfter=6,
        ),
        "sub_heading": ps(
            "sub_heading",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=GREY_DARK,
            leading=13,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ps(
            "body",
            fontName="Helvetica",
            fontSize=10,
            textColor=GREY_DARK,
            leading=14,
            spaceAfter=7,
            alignment=0,
        ),
        "body_tight": ps(
            "body_tight",
            fontName="Helvetica",
            fontSize=9.5,
            textColor=GREY_DARK,
            leading=13,
            spaceAfter=4,
            alignment=0,
        ),
        "small_label": ps(
            "small_label",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            textColor=GREY_MID,
            leading=9,
        ),
        "small_value": ps(
            "small_value",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=NAVY,
            leading=12,
        ),
        "bullet": ps(
            "bullet",
            fontName="Helvetica",
            fontSize=10,
            textColor=GREY_DARK,
            leading=14,
            leftIndent=18,
            firstLineIndent=-8,
            spaceAfter=4,
        ),
        "callout_body": ps(
            "callout_body",
            fontName="Helvetica",
            fontSize=10,
            textColor=GREY_DARK,
            leading=14,
        ),
        "callout_label": ps(
            "callout_label",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=TEAL,
            leading=14,
            spaceAfter=2,
        ),
        "pct_big": ps(
            "pct_big",
            fontName="Helvetica-Bold",
            fontSize=30,
            textColor=TEAL,
            alignment=1,
            leading=36,
        ),
        "pct_label": ps(
            "pct_label",
            fontName="Helvetica",
            fontSize=9,
            textColor=GREY_MID,
            alignment=1,
            leading=12,
        ),
        "step_num": ps(
            "step_num",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=WHITE,
            alignment=1,
            leading=13,
        ),
        "step_title": ps(
            "step_title",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=NAVY,
            leading=13,
            spaceAfter=2,
        ),
        "step_body": ps(
            "step_body",
            fontName="Helvetica",
            fontSize=10,
            textColor=GREY_DARK,
            leading=14,
            spaceAfter=4,
        ),
        "footer": ps(
            "footer",
            fontName="Helvetica",
            fontSize=8,
            textColor=GREY_MID,
            alignment=1,
        ),
        "confidence_badge": ps(
            "confidence_badge",
            fontName="Helvetica-Bold",
            fontSize=10,
            alignment=1,
        ),
    }


S = _styles()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _hr(color=GREY_LINE, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=6, spaceBefore=4)


def _section(title: str, story: list):
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(title.upper(), S["section_heading"]))
    story.append(_hr(TEAL, 1.5))


def _paragraph_chunks(value) -> list[str]:
    text = _text(value, "")
    if not text:
        return []
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", text)]
    return [chunk for chunk in chunks if chunk]


def _add_text_block(value, story: list, style=None):
    style = style or S["body"]
    for chunk in _paragraph_chunks(value):
        story.append(_para(chunk, style, ""))


def _bullets(items: list, story: list):
    for item in items:
        item_text = _strip_list_marker(_text(item, ""))
        if item_text:
            story.append(Paragraph(f"&#8226;  {_inline_text(item_text, '')}", S["bullet"]))


def _info_grid(items: list[tuple[str, object]], story: list):
    cells = []
    for label, value in items:
        cells.append(
            [
                Paragraph(_inline_text(label, ""), S["small_label"]),
                _para(value, S["small_value"], ""),
            ]
        )

    rows = []
    for i in range(0, len(cells), 2):
        row = [cells[i]]
        row.append(cells[i + 1] if i + 1 < len(cells) else "")
        rows.append(row)

    table = Table(rows, colWidths=[PAGE_W / 2 - 0.05 * inch, PAGE_W / 2 - 0.05 * inch], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), GREY_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, GREY_LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.12 * inch))


def _text_panel(title: str, body, story: list, bar_color=TEAL, bg_color=TEAL_LIGHT):
    title_style = ParagraphStyle("panel_title", parent=S["callout_label"], textColor=bar_color)
    title_table = Table([[Paragraph(_inline_text(title, ""), title_style)]], colWidths=[PAGE_W])
    title_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                ("BOX", (0, 0), (-1, -1), 0.5, bar_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(title_table)

    body_style = ParagraphStyle(
        "panel_body",
        parent=S["body"],
        leftIndent=10,
        rightIndent=10,
        spaceBefore=6,
        spaceAfter=6,
    )
    chunks = _paragraph_chunks(body)
    for chunk in chunks:
        story.append(_para(chunk, body_style, ""))
    story.append(Spacer(1, 0.12 * inch))


def _confidence_color(level: str):
    return {
        "High": (GREEN_SOFT, GREEN_BDR, colors.HexColor("#276749")),
        "Medium": (colors.HexColor("#FFFBEB"), colors.HexColor("#F6AD55"), colors.HexColor("#7B341E")),
        "Low": (RED_SOFT, RED_BORDER, colors.HexColor("#9B2335")),
    }.get(level, (TEAL_LIGHT, TEAL, NAVY))


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------
def _cover(report: dict, story: list):
    summary = report.get("summary", {})
    rc = report.get("root_cause", {})
    chances = report.get("reinstatement_chances", {})

    p1_title = Paragraph("Amazon Seller Account", S["cover_title"])
    p1_sub1 = Paragraph("Reinstatement Assessment Report", S["cover_title"])
    p1_sub2 = Paragraph(f"Suspension Cause: {_inline_text(rc.get('most_likely_cause'))}", S["cover_sub"])

    banner_table = Table(
        [[p1_title], [p1_sub1], [p1_sub2]],
        colWidths=[PAGE_W],
    )
    banner_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 18),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 18),
                ("LEFTPADDING", (0, 0), (-1, -1), 20),
                ("RIGHTPADDING", (0, 0), (-1, -1), 20),
                ("ROUNDEDCORNERS", [6]),
            ]
        )
    )
    story.append(banner_table)
    story.append(Spacer(1, 0.25 * inch))

    _info_grid(
        [
            ("Most Likely Cause", rc.get("most_likely_cause")),
            ("Matched Case Type", rc.get("matched_case_type")),
            ("Policies Identified", ", ".join(summary.get("key_policies_identified", [])) or "-"),
        ],
        story,
    )

    ctx = summary.get("suspension_context", "")
    if ctx:
        _text_panel("Suspension Context", ctx, story)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------
def _section_root_cause(rc: dict, story: list):
    _section("2. Root Cause Identification", story)

    _text_panel("Most Likely Cause", rc.get("most_likely_cause"), story, bar_color=NAVY, bg_color=GREY_LIGHT)

    matched = rc.get("matched_case_type", "")
    if matched:
        story.append(Paragraph(f"<b>Matched Case Type:</b> {_inline_text(matched)}", S["body"]))
        story.append(Spacer(1, 0.04 * inch))

    policies = rc.get("policy_sections", [])
    if policies:
        story.append(Paragraph("<b>Policy Sections Referenced:</b>", S["sub_heading"]))
        _bullets(policies, story)
        story.append(Spacer(1, 0.04 * inch))

    evidence = rc.get("evidence", [])
    if evidence:
        story.append(Paragraph("<b>Supporting Evidence from Notification:</b>", S["sub_heading"]))
        _bullets(evidence, story)
        story.append(Spacer(1, 0.04 * inch))


def _section_documents(docs: dict, story: list):
    _section("3. Document Checklist", story)

    comparison = docs.get("comparison", [])
    if not comparison:
        story.append(Paragraph("No document data available.", S["body"]))
        return

    available_count = sum(1 for item in comparison if item.get("available", False))
    required_count = sum(1 for item in comparison if item.get("required", False))
    missing = [
        item.get("document", "")
        for item in comparison
        if item.get("required", False) and not item.get("available", False)
    ]
    _info_grid(
        [
            ("Required Documents", required_count),
            ("Available Documents", available_count),
            ("Missing Documents", len(missing)),
            ("Document Readiness", f"{available_count}/{required_count}" if required_count else "-"),
        ],
        story,
    )

    header = [
        Paragraph("<b>Document</b>", S["sub_heading"]),
        Paragraph("<b>Required</b>", S["sub_heading"]),
        Paragraph("<b>Available</b>", S["sub_heading"]),
    ]
    rows = [header]
    for item in comparison:
        req = item.get("required", False)
        avl = item.get("available", False)
        tick_req = Paragraph(
            '<font color="#276749">&#10003;</font>' if req else '<font color="#9B2335">&#10007;</font>',
            ParagraphStyle("tc", alignment=1, fontSize=11),
        )
        tick_avl = Paragraph(
            '<font color="#276749">&#10003;</font>' if avl else '<font color="#9B2335">&#10007;</font>',
            ParagraphStyle("tc", alignment=1, fontSize=11),
        )
        rows.append([_para(item.get("document", ""), S["body"], ""), tick_req, tick_avl])

    tbl = Table(rows, colWidths=[PAGE_W * 0.62, PAGE_W * 0.19, PAGE_W * 0.19], repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.4, GREY_LINE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(tbl)


def _section_chances(chances: dict, story: list):
    _section("4. Reinstatement Chance Calculation", story)

    _text_panel(
        "How to Read This",
        (
            "The first score reflects the case using the documents currently available. "
            "The second score assumes the missing documents are gathered before SPCTEK prepares the appeal."
        ),
        story,
        bar_color=GOLD,
        bg_color=colors.HexColor("#FFFBEB"),
    )

    pct1 = _text(chances.get("percentage_1_current_docs"))
    pct2 = _text(chances.get("percentage_2_with_all_docs"))
    pct_table = Table(
        [
            [
                [
                    _para(pct1, S["pct_big"]),
                    Paragraph("With Current Documents\n+ SPCTEK Guided Appeal", S["pct_label"]),
                ],
                [
                    _para(pct2, S["pct_big"]),
                    Paragraph("After Obtaining All Missing\nDocuments + SPCTEK Support", S["pct_label"]),
                ],
            ]
        ],
        colWidths=[PAGE_W / 2, PAGE_W / 2],
    )
    pct_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), TEAL_LIGHT),
                ("BACKGROUND", (1, 0), (1, -1), GREEN_SOFT),
                ("BOX", (0, 0), (0, -1), 1, TEAL),
                ("BOX", (1, 0), (1, -1), 1, GREEN_BDR),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(pct_table)


def _section_steps(steps: list, story: list):
    _section("5. Recommended Reinstatement Steps", story)

    for step in steps:
        num = str(step.get("step", ""))
        title = step.get("title", "")
        desc = step.get("description", "")

        badge_cell = Table([[Paragraph(num, S["step_num"])]], colWidths=[0.3 * inch], rowHeights=[0.28 * inch])
        badge_cell.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), TEAL),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROUNDEDCORNERS", [3]),
                ]
            )
        )

        body_parts = [_para(title, S["step_title"], "")]
        body_parts.extend(_para(chunk, S["step_body"], "") for chunk in _paragraph_chunks(desc))

        step_card = Table([[badge_cell, body_parts]], colWidths=[0.44 * inch, PAGE_W - 0.44 * inch])
        step_card.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), GREY_LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.5, GREY_LINE),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (0, -1), 8),
                    ("RIGHTPADDING", (0, 0), (0, -1), 4),
                    ("LEFTPADDING", (1, 0), (1, -1), 10),
                    ("RIGHTPADDING", (1, 0), (1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            )
        )

        block = KeepTogether([step_card, Spacer(1, 0.08 * inch)])
        story.append(block)


def _section_poa(poa: dict, story: list):
    _section("6. Plan of Action Guidance", story)

    structure = poa.get("structure", [])
    if structure:
        story.append(Paragraph("<b>POA Structure</b>", S["sub_heading"]))
        panel_story = []
        _bullets(structure, panel_story)
        panel = Table([[panel_story]], colWidths=[PAGE_W])
        panel.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), GREY_LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.5, GREY_LINE),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        story.append(panel)
        story.append(Spacer(1, 0.1 * inch))

    key_points = poa.get("key_points_to_address", [])
    if key_points:
        story.append(Paragraph("<b>Key Points to Address</b>", S["sub_heading"]))
        _bullets(key_points, story)
        story.append(Spacer(1, 0.08 * inch))

    template = poa.get("template_outline", "")
    if template:
        story.append(Paragraph("<b>Template Outline</b>", S["sub_heading"]))
        for line in template.split("\n"):
            line_text = _strip_list_marker(_text(line, ""))
            if line_text:
                story.append(Paragraph(f"&#8226;  {_inline_text(line_text, '')}", S["bullet"]))


def _section_summary(fs: dict, story: list):
    _section("7. Final Summary", story)

    conclusion = fs.get("conclusion", "")
    if conclusion:
        _text_panel("Conclusion", conclusion, story, bar_color=NAVY, bg_color=GREY_LIGHT)

    next_steps = fs.get("immediate_next_steps", [])
    if next_steps:
        story.append(Paragraph("<b>Immediate Next Steps</b>", S["sub_heading"]))
        _bullets(next_steps, story)


def _add_page_decorations(canvas, doc):
    canvas.saveState()
    w, h = letter

    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 0.18 * inch, w, 0.18 * inch, stroke=0, fill=1)

    canvas.setFillColor(GREY_MID)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawCentredString(w / 2, 0.35 * inch, "SPCTEK - Amazon Seller Reinstatement Specialist")
    canvas.drawRightString(w - 0.75 * inch, 0.35 * inch, f"Page {doc.page}")
    canvas.setStrokeColor(GREY_LINE)
    canvas.setLineWidth(0.5)
    canvas.line(0.75 * inch, 0.52 * inch, w - 0.75 * inch, 0.52 * inch)

    canvas.restoreState()


def write_formatted_report(report: dict, filename: str = "report.pdf"):
    if "report" in report:
        report = report["report"]

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.75 * inch,
    )

    story = []
    _cover(report, story)
    summary = report.get("summary", {})
    _section("1. Suspension Summary", story)
    _text_panel("Case Context", summary.get("suspension_context"), story)
    policies = summary.get("key_policies_identified", [])
    if policies:
        story.append(Paragraph("<b>Key Policies Identified:</b>", S["sub_heading"]))
        _bullets(policies, story)

    _section_root_cause(report.get("root_cause", {}), story)
    _section_documents(report.get("documents", {}), story)
    _section_chances(report.get("reinstatement_chances", {}), story)
    steps = report.get("recommended_steps", [])
    if steps:
        _section_steps(steps, story)
    poa = report.get("poa_guidance", {})
    if poa:
        _section_poa(poa, story)
    fs = report.get("final_summary", {})
    if fs:
        _section_summary(fs, story)

    doc.build(story, onFirstPage=_add_page_decorations, onLaterPages=_add_page_decorations)
