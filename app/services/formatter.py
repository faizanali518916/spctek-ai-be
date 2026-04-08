import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

# Usable width with 0.75" margins each side
PAGE_WIDTH = 6.5 * inch


def write_formatted_report(text: str, filename="report.pdf"):
    """Generate a formatted PDF report from markdown text."""

    # Strip markdown code block wrappers (```plaintext ... ```)
    text = re.sub(r"^```[a-z]*\n?", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\n?```$", "", text.strip(), flags=re.MULTILINE)
    text = text.strip()

    # Find and strip intro text before the numbered report body
    lines = text.split("\n")
    report_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Report body starts at the first numbered section heading like "### **1."
        if re.match(r"^#+\s*\*?\*?\d+\.", stripped):
            report_start = i
            break
    text = "\n".join(lines[report_start:])

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=20,
        alignment=1,
        fontName="Helvetica-Bold",
    )
    heading1_style = ParagraphStyle(
        "CustomHeading1",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=8,
        spaceBefore=14,
        fontName="Helvetica-Bold",
        borderPad=4,
    )
    heading2_style = ParagraphStyle(
        "CustomHeading2",
        parent=styles["Heading3"],
        fontSize=12,
        textColor=colors.HexColor("#34495e"),
        spaceAfter=6,
        spaceBefore=10,
        fontName="Helvetica-Bold",
    )
    normal_style = ParagraphStyle(
        "CustomNormal",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=8,
        leading=14,
        alignment=4,
    )
    bullet_style = ParagraphStyle(
        "CustomBullet",
        parent=styles["Normal"],
        fontSize=10,
        leftIndent=18,
        firstLineIndent=0,
        spaceAfter=5,
        leading=13,
    )
    sub_bullet_style = ParagraphStyle(
        "CustomSubBullet",
        parent=styles["Normal"],
        fontSize=10,
        leftIndent=36,
        firstLineIndent=0,
        spaceAfter=4,
        leading=13,
    )

    story = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        raw = line.strip()

        # Skip blank lines
        if not raw:
            i += 1
            continue

        # Skip horizontal rules
        if re.match(r"^-{3,}$", raw):
            story.append(Spacer(1, 0.12 * inch))
            i += 1
            continue

        # ---- HEADINGS ----
        # #### or ### or ## headings - strip hashes and bold markers
        if raw.startswith("#"):
            level = len(re.match(r"^(#+)", raw).group(1))
            heading_text = re.sub(r"^#+\s*", "", raw)
            heading_text = _strip_bold(heading_text)  # remove **...**
            heading_text = _process_inline_formatting(heading_text)
            if level <= 3:
                story.append(Paragraph(heading_text, heading1_style))
            else:
                story.append(Paragraph(heading_text, heading2_style))
            i += 1
            continue

        # ---- TABLE (markdown pipe tables) ----
        if raw.startswith("|"):
            table_end = i
            while table_end < len(lines) and lines[table_end].strip().startswith("|"):
                table_end += 1

            table_lines = [l.strip() for l in lines[i:table_end]]
            table_data = []
            for tline in table_lines:
                # Skip separator rows like |---|---|
                if re.match(r"^\|[\s\-:|]+\|", tline):
                    continue
                cells = [c.strip() for c in tline.split("|")]
                cells = [c for c in cells if c != ""]
                if cells:
                    # Strip bold markers from table cells
                    cells = [_strip_bold(c) for c in cells]
                    table_data.append(cells)

            if len(table_data) >= 2:
                num_cols = len(table_data[0])
                # Give the first column more space, split remaining evenly
                if num_cols == 3:
                    col_widths = [
                        PAGE_WIDTH * 0.55,
                        PAGE_WIDTH * 0.225,
                        PAGE_WIDTH * 0.225,
                    ]
                elif num_cols == 2:
                    col_widths = [PAGE_WIDTH * 0.65, PAGE_WIDTH * 0.35]
                else:
                    col_widths = [PAGE_WIDTH / num_cols] * num_cols
                table = Table(table_data, colWidths=col_widths, repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.HexColor("#f0f4f8")],
                            ),
                            ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
                        ]
                    )
                )
                story.append(Spacer(1, 0.1 * inch))
                story.append(table)
                story.append(Spacer(1, 0.15 * inch))

            i = table_end
            continue

        # ---- SUB-BULLETS (indented with spaces + * or -)  ----
        # Matches lines like "    *   text" or "        - text"
        if re.match(r"^\s{2,}[*\-]\s+", line):
            text_content = re.sub(r"^\s+[*\-]\s+", "", line)
            text_content = _process_inline_formatting(text_content)
            story.append(Paragraph(f"&#8226; {text_content}", sub_bullet_style))
            i += 1
            continue

        # ---- NUMBERED SUB-ITEMS (indented "    1." or "    2.") ----
        if re.match(r"^\s{2,}\d+\.\s+", line):
            text_content = re.sub(r"^\s+\d+\.\s+", "", line)
            text_content = _process_inline_formatting(text_content)
            story.append(Paragraph(f"&#8226; {text_content}", sub_bullet_style))
            i += 1
            continue

        # ---- BULLETS: *, •, - at start of line  ----
        if re.match(r"^[*•\-]\s+", raw):
            text_content = re.sub(r"^[*•\-]\s+", "", raw)
            text_content = _process_inline_formatting(text_content)
            story.append(Paragraph(f"&#8226; {text_content}", bullet_style))
            i += 1
            continue

        # ---- NUMBERED LIST at start of line ----
        if re.match(r"^\d+\.\s+", raw):
            num = re.match(r"^(\d+)\.\s+", raw).group(1)
            text_content = re.sub(r"^\d+\.\s+", "", raw)
            text_content = _process_inline_formatting(text_content)
            story.append(Paragraph(f"<b>{num}.</b> {text_content}", bullet_style))
            i += 1
            continue

        # ---- NORMAL PARAGRAPH ----
        text_content = _process_inline_formatting(raw)
        if text_content.strip():
            story.append(Paragraph(text_content, normal_style))

        i += 1

    doc.build(story)


def _strip_bold(text: str) -> str:
    """Remove **...** markers (used for headings where bold is redundant)."""
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", text).strip()


def _process_inline_formatting(text: str) -> str:
    """Convert markdown inline formatting to ReportLab XML tags."""
    text = re.sub(r"\*{3,}", "", text)  # strip triple+ asterisks
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", text)  # bold
    text = re.sub(r"\*([^*\n]+)\*", r"<i>\1</i>", text)  # italic
    text = re.sub(r"(?<!\*)\*(?!\*)", "", text)  # stray lone asterisks
    return text.strip()
