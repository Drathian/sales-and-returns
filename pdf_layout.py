"""How the PDF report looks: colours, text styles, charts, tables and the page footer.

main.py decides what goes in the report; this file only decides how it looks.
"""
import io
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")  # draw charts into images instead of opening windows
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (CondPageBreak, HRFlowable, Image, KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

# Colours. Blue and orange are checked to stay distinct for colour-blind readers.
BLUE = "#2a78d6"     # main data colour
ORANGE = "#eb6834"   # second series and highlighted points
GREY = "#c3c2b7"     # context bars and chart baselines
INK = "#0b0b0b"      # main text
INK_2 = "#52514e"    # secondary text and values
MUTED = "#898781"    # captions and footer
GRID = "#e1e0d9"     # hairlines
TILE = "#f3f3f0"     # background behind headline numbers

MARGIN = 18 * mm
WIDTH = A4[0] - 2 * MARGIN  # usable page width, in points

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 7.5,
    "text.color": INK,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "axes.titlesize": 8,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.titlecolor": INK,
    "legend.frameon": False,
})


# ---------- Number formats ----------

def sek(value):
    return f"SEK {value:,.0f}"


def sek_m(value):
    return f"SEK {value / 1e6:,.1f}M"


def pct(fraction, decimals=1):
    return f"{fraction:.{decimals}%}"


def signed_pct(fraction):
    return f"{fraction:+.1%}"


def day(moment):
    return f"{moment.day} {moment:%b %Y}"


# ---------- Text ----------

def _style(name, size, font="Helvetica", color=INK, **extra):
    settings = {"fontName": font, "fontSize": size, "leading": size * 1.35, "textColor": colors.HexColor(color)}
    return ParagraphStyle(name, **{**settings, **extra})


BOLD = "Helvetica-Bold"
STYLES = {
    "overline": _style("overline", 7.5, BOLD, MUTED),
    "title": _style("title", 26, BOLD, leading=31, spaceBefore=6, spaceAfter=8),
    "subtitle": _style("subtitle", 11.5, color=INK_2),
    "meta": _style("meta", 8, color=MUTED, spaceBefore=4),
    "section": _style("section", 17, BOLD, spaceBefore=26),  # the space is skipped at the top of a page
    "headline": _style("headline", 11.5, BOLD, spaceBefore=16, spaceAfter=3),
    "body": _style("body", 9, color=INK_2),
    "caption": _style("caption", 7.5, color=MUTED, spaceBefore=4),
    "finding": _style("finding", 10.5, BOLD, spaceAfter=2),
    "number": _style("number", 14, BOLD, BLUE),
    "kpi_label": _style("kpi_label", 8, color=INK_2),
    "kpi_value": _style("kpi_value", 19, BOLD, spaceBefore=3, spaceAfter=3),
    "kpi_note": _style("kpi_note", 7.5, color=MUTED),
    "th": _style("th", 7.5, BOLD, INK_2, alignment=TA_RIGHT),
    "th_left": _style("th_left", 7.5, BOLD, INK_2),
    "term": _style("term", 8.5, BOLD),
}


def text(content, style="body"):
    """A paragraph in one of the STYLES. Characters like & are escaped automatically."""
    return Paragraph(escape(content), STYLES[style])


def section(title):
    """A big section heading with a line under it. Starts a new page if there isn't room
    for the heading and the first chart."""
    return [CondPageBreak(340), text(title, "section"),
            HRFlowable(width="100%", thickness=0.6, color=colors.HexColor(GRID), spaceBefore=6, spaceAfter=2)]


def block(headline, detail, *content, caption=None):
    """A headline, an optional sentence, the content (charts, tables) and an optional
    caption, kept together on the same page."""
    parts = [text(headline, "headline")]
    if detail:
        parts.append(text(detail))
    parts += [Spacer(1, 6), *content]
    if caption:
        parts.append(text(caption, "caption"))
    return KeepTogether(parts)


def findings(items):
    """Numbered key findings. items: list of (headline, detail)."""
    rows = [[text(str(number), "number"), [text(headline, "finding"), text(detail)]]
            for number, (headline, detail) in enumerate(items, start=1)]
    table = Table(rows, colWidths=[24, WIDTH - 24])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor(GRID)),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


# ---------- Tables ----------

def kpi_tiles(tiles, columns=3):
    """Headline numbers in tiles. tiles: list of (label, value, note) that fills whole rows."""
    cells = [[text(label, "kpi_label"), text(value, "kpi_value"), text(note, "kpi_note")]
             for label, value, note in tiles]
    table = Table([cells[i:i + columns] for i in range(0, len(cells), columns)], colWidths=[WIDTH / columns] * columns)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(TILE)),
        ("GRID", (0, 0), (-1, -1), 6, colors.white),  # white gaps between the tiles
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    return table


def data_table(header, rows, widths, bold_cells=(), numbers=True):
    """A table with a header row and hairlines between rows.
    numbers: right-align every column except the first.
    bold_cells: (column, row) positions to make bold, counting the header as row 0."""
    head = [text(title, "th" if numbers and i else "th_left") for i, title in enumerate(header)]
    table = Table([head] + rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor(INK)),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT" if numbers else "LEFT"),
        ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
        ("VALIGN", (0, 1), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(INK_2)),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor(GRID)),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ] + [("FONT", cell, cell, BOLD, 8) for cell in bold_cells]))
    return table


# ---------- Charts ----------

def _figure(height, panels=1):
    """An empty chart as wide as the page, with one or more panels side by side."""
    return plt.subplots(1, panels, figsize=(WIDTH / 72, height / 72), sharey=True, squeeze=False,
                        layout="constrained")


def _keep_only(ax, side):
    """Remove the chart frame except one thin baseline."""
    for name, spine in ax.spines.items():
        spine.set_visible(name == side)
        spine.set_color(GREY)
    ax.tick_params(length=0)


def _image(fig, height):
    """The chart as an image that fits the page width."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=220)
    plt.close(fig)
    buffer.seek(0)
    return Image(buffer, width=WIDTH, height=height)


def bar_chart(labels, panels, highlight=None):
    """Horizontal bars. Each panel shows one measure for the same labels.

    panels: list of (title, values, value_format), with an optional 4th item that
    draws a reference line, e.g. the average.
    highlight: labels to draw in blue, the rest grey. None draws all bars blue.
    """
    height = 26 + 16 * len(labels)
    fig, axes = _figure(height, len(panels))
    rows = range(len(labels))
    bar_colors = [BLUE if highlight is None or label in highlight else GREY for label in labels]
    for ax, (title, values, value_format, *reference) in zip(axes[0], panels):
        ax.barh(rows, values, height=0.62, color=bar_colors)
        for row, value in zip(rows, values):  # white behind the label so a reference line can't cross it
            ax.annotate(value_format.format(value), (value, row), xytext=(4, 0), textcoords="offset points",
                        va="center", color=INK_2, bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
        for value in reference:
            ax.axvline(value, color=INK_2, linewidth=0.8)
        ax.set_title(title)
        ax.set_xlim(0, max(values) * 1.3)
        ax.xaxis.set_visible(False)
        _keep_only(ax, "left")
    axes[0][0].set_yticks(rows, labels)
    axes[0][0].invert_yaxis()
    return _image(fig, height)


def line_chart(dates, values, title, marked, marked_label):
    """A line over time. Points where `marked` is True get an orange dot."""
    height = 185
    fig, axes = _figure(height)
    ax = axes[0][0]
    ax.plot(dates, values, color=BLUE, linewidth=1.6, solid_joinstyle="round", solid_capstyle="round")
    ax.fill_between(dates, values, color=BLUE, alpha=0.08, linewidth=0)
    ax.scatter([d for d, m in zip(dates, marked) if m], [v for v, m in zip(values, marked) if m],
               s=24, color=ORANGE, edgecolors="white", linewidths=1.2, zorder=3, label=marked_label)
    ax.legend(loc="upper left")
    ax.set_title(title)
    ax.set_ylim(0, max(values) * 1.15)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    _keep_only(ax, "bottom")
    return _image(fig, height)


def stacked_columns(labels, series, title):
    """Columns made of two stacked parts. series: [(name, values), (name, values)]."""
    height = 185
    fig, axes = _figure(height)
    ax = axes[0][0]
    totals = [sum(parts) for parts in zip(*(values for _, values in series))]
    bottoms = [0] * len(labels)
    for (name, values), color, label_color in zip(series, (BLUE, ORANGE), ("white", INK)):
        ax.bar(labels, values, bottom=bottoms, width=0.42, color=color, edgecolor="white", linewidth=1.5, label=name)
        for x, (bottom, value) in enumerate(zip(bottoms, values)):
            if value > 0.07 * max(totals):  # only label parts big enough to hold the number
                ax.text(x, bottom + value / 2, f"{value:,.0f}", ha="center", va="center", color=label_color)
        bottoms = [b + v for b, v in zip(bottoms, values)]
    for x, total in enumerate(totals):
        ax.annotate(f"{total:,.0f}", (x, total), xytext=(0, 3), textcoords="offset points", ha="center",
                    fontweight="bold")
    ax.legend(loc="upper left", ncols=len(series))
    ax.set_title(title)
    ax.set_ylim(0, max(totals) * 1.25)
    ax.yaxis.set_visible(False)
    _keep_only(ax, "bottom")
    return _image(fig, height)


# ---------- The document ----------

def build_pdf(path, story, title):
    """Write the story (list of PDF parts) to a file with a footer on every page."""
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor(GRID))
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 13 * mm, A4[0] - MARGIN, 13 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(MARGIN, 9 * mm, title)
        canvas.drawRightString(A4[0] - MARGIN, 9 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(path, pagesize=A4, title=title, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=MARGIN, bottomMargin=20 * mm)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
