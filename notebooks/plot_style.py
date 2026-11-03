"""Shared look for every chart in the project.

Import it once at the top of a notebook (`import plot_style`) and every Plotly
figure after that picks up the same fonts, colors, and gridlines.
"""
import plotly.graph_objects as go
import plotly.io as pio

# Series colors. Checked for colorblind separation (blue vs. orange).
METRO = "#2a78d6"
RURAL = "#eb6834"
COLORS = {"Metro": METRO, "Rural": RURAL}

# One-hue sequential ramp (light = low, dark = high) for maps.
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

# Diverging scale for values above/below zero: blue = below, gray = about zero, red = above.
DIVERGING = [[0.0, "#184f95"], [0.25, "#6da7ec"], [0.5, "#f0efec"], [0.75, "#ec8a7e"], [1.0, "#a8282a"]]

# Ink and chrome.
INK = "#0b0b0b"        # titles
INK_2 = "#52514e"      # body text
MUTED = "#898781"      # tick labels, notes
GRID = "#e1e0d9"       # gridlines
AXIS = "#c3c2b7"       # axis lines
SURFACE = "#fcfcfb"    # chart background
NO_DATA = "#e8e7e2"    # counties with no data on maps

FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"

_axis = dict(gridcolor=GRID, linecolor=AXIS, showline=True, zeroline=False,
             ticks="", tickfont=dict(color=MUTED), title=dict(font=dict(color=INK_2)))

pio.templates["medicare"] = go.layout.Template(layout=dict(
    font=dict(family=FONT, size=13, color=INK_2),
    title=dict(font=dict(size=18, color=INK), x=0, xanchor="left", xref="paper"),
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    xaxis=_axis,
    yaxis=_axis,
    legend=dict(orientation="h", x=0, y=1.0, yanchor="bottom", title=None),
    hoverlabel=dict(bgcolor="white", bordercolor=AXIS, font=dict(family=FONT, color=INK)),
    margin=dict(l=70, r=30, t=100, b=60),
))
pio.templates.default = "plotly_white+medicare"


def subtitle(title, sub):
    """Plotly title with a smaller gray subtitle line underneath."""
    return f"{title}<br><span style='font-size:13px;color:{MUTED}'>{sub}</span>"


# ---------------------------------------------------------------- website export
SITE_CHARTS = "../site/medicare/charts"

# Lets a chart fill the full height of the iframe it sits in on the web page.
_FILL = "<style>html,body{height:100%;margin:0;background:#fcfcfb}body>div{height:100%}</style>"


def site_copy(fig):
    """A copy of `fig` for the website: no title (the page has headings) and no fixed height."""
    web = go.Figure(fig)
    web.update_layout(title=None, height=None, autosize=True, margin_t=50)
    return web


def write_site_chart(fig, name):
    """Save `fig` as site/medicare/charts/<name>.html, loading Plotly from its CDN."""
    import os

    os.makedirs(SITE_CHARTS, exist_ok=True)
    path = f"{SITE_CHARTS}/{name}.html"
    fig.write_html(path, include_plotlyjs="cdn", full_html=True, default_height="100%",
                   config={"displayModeBar": False, "responsive": True})
    with open(path) as f:
        html = f.read().replace("</head>", _FILL + "</head>", 1)
    with open(path, "w") as f:
        f.write(html)
    print(f"{path}  ({os.path.getsize(path) / 1e6:.1f} MB)")
    return path
