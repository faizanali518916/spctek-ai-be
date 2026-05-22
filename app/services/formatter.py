"""
formatter.py
Renders a parsed reinstatement-report JSON dict into a polished PDF
using ReportLab Platypus.
"""

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
            leading=15,
            spaceAfter=6,
            alignment=4,
        ),
        "bullet": ps(
            "bullet",
            fontName="Helvetica",
            fontSize=10,
            textColor=GREY_DARK,
            leading=14,
            leftIndent=14,
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


def _bullets(items: list, story: list):
    for item in items:
        if item.strip():
            story.append(Paragraph(f"&#8226;  {item}", S["bullet"]))


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
    p1_sub2 = Paragraph(
        f"Suspension Cause: {rc.get('most_likely_cause', '—')}",
        S["cover_sub"],
    )

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

    pct1 = chances.get("percentage_1_current_docs", "—")
    pct2 = chances.get("percentage_2_with_all_docs", "—")

    def _pct_cell(pct, label):
        return [Paragraph(pct, S["pct_big"]), Paragraph(label, S["pct_label"])]

    pct_table = Table(
        [
            [
                _pct_cell(pct1, "Reinstatement Chance\n(Current Documents)"),
                _pct_cell(pct2, "Reinstatement Chance\n(After Obtaining All Docs)"),
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
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROUNDEDCORNERS", [4]),
            ]
        )
    )
    story.append(pct_table)
    story.append(Spacer(1, 0.2 * inch))

    ctx = summary.get("suspension_context", "")
    if ctx:
        story.append(Paragraph("<b>Suspension Context</b>", S["sub_heading"]))
        story.append(Paragraph(ctx, S["body"]))
        story.append(Spacer(1, 0.1 * inch))


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------
def _section_root_cause(rc: dict, story: list):
    _section("2. Root Cause Identification", story)

    cause = rc.get("most_likely_cause", "—")
    story.append(Paragraph(f"<b>Most Likely Cause:</b> {cause}", S["body"]))

    matched = rc.get("matched_case_type", "")
    if matched:
        story.append(Paragraph(f"<b>Matched Case Type:</b> {matched}", S["body"]))

    policies = rc.get("policy_sections", [])
    if policies:
        story.append(Paragraph("<b>Policy Sections Referenced:</b>", S["sub_heading"]))
        _bullets(policies, story)

    evidence = rc.get("evidence", [])
    if evidence:
        story.append(Paragraph("<b>Supporting Evidence from Notification:</b>", S["sub_heading"]))
        _bullets(evidence, story)

    confidence = rc.get("confidence", "Medium")
    bg, border, txt_color = _confidence_color(confidence)
    badge_style = ParagraphStyle("badge", parent=S["confidence_badge"], textColor=txt_color)
    badge = Table([[Paragraph(f"AI Confidence: {confidence}", badge_style)]], colWidths=[1.6 * inch])
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 1, border),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("ROUNDEDCORNERS", [4]),
            ]
        )
    )
    story.append(Spacer(1, 0.06 * inch))
    story.append(badge)


def _section_documents(docs: dict, story: list):
    _section("3. Document Checklist", story)

    comparison = docs.get("comparison", [])
    if not comparison:
        story.append(Paragraph("No document data available.", S["body"]))
        return

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
        rows.append([Paragraph(item.get("document", ""), S["body"]), tick_req, tick_avl])

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

    ci = chances.get("calculation_inputs", {})
    if ci:
        rows = [
            [Paragraph("<b>Factor</b>", S["sub_heading"]), Paragraph("<b>Value</b>", S["sub_heading"])],
            ["Business Model", str(ci.get("business_model", "—"))],
            ["Business Model Factor", str(ci.get("business_model_factor", "—"))],
            ["Documents Required", str(ci.get("documents_required_count", "—"))],
            ["Documents Available", str(ci.get("documents_available_count", "—"))],
            ["Doc Completeness Score", str(ci.get("doc_completeness_score", "—"))],
            ["Appeals Made", str(ci.get("appeals_made", "—"))],
            ["Appeals Penalty", str(ci.get("appeals_penalty", "—"))],
            ["Confidence Factor", str(ci.get("confidence_factor", "—"))],
        ]
        fmt_rows = []
        for r in rows:
            fmt_rows.append(
                [
                    r[0] if isinstance(r[0], Paragraph) else Paragraph(str(r[0]), S["body"]),
                    r[1] if isinstance(r[1], Paragraph) else Paragraph(str(r[1]), S["body"]),
                ]
            )

        tbl = Table(fmt_rows, colWidths=[PAGE_W * 0.6, PAGE_W * 0.4], repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("GRID", (0, 0), (-1, -1), 0.4, GREY_LINE),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(tbl)
        story.append(Spacer(1, 0.15 * inch))

    pct1 = chances.get("percentage_1_current_docs", "—")
    pct2 = chances.get("percentage_2_with_all_docs", "—")
    pct_table = Table(
        [
            [
                [
                    Paragraph(pct1, S["pct_big"]),
                    Paragraph("With Current Documents\n+ SPCTEK Guided Appeal", S["pct_label"]),
                ],
                [
                    Paragraph(pct2, S["pct_big"]),
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

        header_row = Table(
            [[badge_cell, Paragraph(title, S["step_title"])]], colWidths=[0.38 * inch, PAGE_W - 0.38 * inch]
        )
        header_row.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (1, 0), (1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        block = KeepTogether(
            [header_row, Spacer(1, 0.04 * inch), Paragraph(desc, S["step_body"]), Spacer(1, 0.06 * inch)]
        )
        story.append(block)


def _section_poa(poa: dict, story: list):
    _section("6. Plan of Action Guidance", story)

    structure = poa.get("structure", [])
    if structure:
        story.append(Paragraph("<b>POA Structure</b>", S["sub_heading"]))
        _bullets(structure, story)

    key_points = poa.get("key_points_to_address", [])
    if key_points:
        story.append(Paragraph("<b>Key Points to Address</b>", S["sub_heading"]))
        _bullets(key_points, story)

    template = poa.get("template_outline", "")
    if template:
        story.append(Paragraph("<b>Template Outline</b>", S["sub_heading"]))
        for line in template.split("\n"):
            if line.strip():
                story.append(Paragraph(f"&#8226;  {line}", S["bullet"]))


def _section_summary(fs: dict, story: list):
    _section("7. Final Summary", story)

    conclusion = fs.get("conclusion", "")
    if conclusion:
        story.append(Paragraph("<b>Conclusion</b>", S["sub_heading"]))
        story.append(Paragraph(conclusion, S["body"]))
        story.append(Spacer(1, 0.1 * inch))

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
    canvas.drawCentredString(w / 2, 0.35 * inch, "SPCTEK — Amazon Seller Reinstatement Specialist")
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
    story.append(Paragraph(summary.get("suspension_context", "—"), S["body"]))
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
