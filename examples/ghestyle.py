"""The look of GHE Analysis's charts, for matplotlib.

The notebooks draw their figures the way the application does, so that a curve is the same colour
here as on the panel it comes from, and a legend reads the same. The values are those of the
application's own chart code: the palette of the Charts panel, the sign-dependent colouring of the
loads, the stacked bands of the Borehole designer, and the hue ramp of the thermal contour.

    import ghestyle as ghe
    ghe.use()                              # once, at the top of a notebook
    fig, ax = ghe.figure()
    ghe.signed_line(ax, t, load, above=ghe.ORANGE, below=ghe.GREEN)
    ghe.legend(ax, [(ghe.ORANGE, "Heating - Demand"), (ghe.GREEN, "Cooling - Demand")])
"""

import colorsys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

# The palette of the Charts panel (widget11Charts.h).
RED = "#EA3E08"
RED2 = "#F1815E"
ORANGE = "#FFA300"
GREEN = "#9ACA54"
BLUE = "#40ABFF"
BLUE2 = "#83C8FF"
BLACK = "#000000"

BACKGROUND = "#FCFCFC"      # panel and plot area
GRID = "#E8E8E8"            # grid lines (shared/chartstyle.h)
AXIS = "#B5B5B5"            # axis lines and ticks

# Meaning of the colours, as the panels use them.
HEATING = RED
COOLING = BLUE


def _font():
    """The application's font when the machine has it, else the best neighbour."""
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Segoe UI Semilight", "Segoe UI", "Helvetica Neue", "Helvetica", "Arial"):
        if name in available:
            return name
    return "DejaVu Sans"


def use():
    """Applies the application's chart style to every figure that follows."""
    mpl.rcParams.update({
        "figure.facecolor": BACKGROUND,
        "axes.facecolor": BACKGROUND,
        "savefig.facecolor": BACKGROUND,
        "figure.dpi": 100,
        "savefig.dpi": 100,
        "font.family": _font(),
        "font.size": 9,
        "mathtext.default": "regular",
        "axes.labelsize": 9,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": "black",
        "ytick.color": "black",
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.labelcolor": "black",
        "text.color": "black",
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "lines.linewidth": 1.0,
        "lines.solid_capstyle": "butt",
        "figure.constrained_layout.use": True,
    })


def figure(width=8.6, height=3.3, **kwargs):
    """A figure with one set of axes, sized like the application's chart panel."""
    fig, ax = plt.subplots(figsize=(width, height), **kwargs)
    return fig, ax


def legend(ax, entries, outside=True, ncol=1, loc="upper right"):
    """A legend of coloured squares, as the panels draw it.

    entries: (colour, label) pairs, in reading order. Labels may use mathtext for subscripts,
    for instance "Heating T$_{Lim}$". The panels keep the legend at the right edge of the chart;
    outside=True does the same here, so that it never hides a curve; with outside=False the legend
    goes inside the axes, at `loc`.
    """
    handles = [Patch(facecolor=colour, edgecolor="none", label=label) for colour, label in entries]
    where = {"loc": "upper left", "bbox_to_anchor": (1.01, 1.0)} if outside else {"loc": loc}
    ax.legend(handles=handles, ncol=ncol, handlelength=0.75, handleheight=0.75,
              handletextpad=0.5, labelspacing=0.45, borderaxespad=0.0, **where)


def signed_line(ax, x, y, above, below, linewidth=1.0, **kwargs):
    """A line drawn in one colour where y >= 0 and in another where y < 0.

    This is how the application colours its loads: the sign says heating or cooling, so the colour
    changes at the zero line without the legend having to follow the curve.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    points = np.column_stack([x, y])
    segments = np.stack([points[:-1], points[1:]], axis=1)
    middle = 0.5 * (y[:-1] + y[1:])
    colours = np.where(middle >= 0, above, below)
    collection = LineCollection(segments, colors=colours, linewidths=linewidth, **kwargs)
    ax.add_collection(collection)
    ax.autoscale_view()
    return collection


def hue_colours(n):
    """The n colours of the thermal contour, from blue (lowest level) to red (highest).

    thermalcontour.cpp sets hue = (n - 1 - k) / (n - 1) * 240 degrees, saturation 220/255, value 1.
    """
    top = max(1, n - 1)
    return [colorsys.hsv_to_rgb((top - k) / top * 240.0 / 360.0, 220 / 255, 1.0) for k in range(n)]


def hue_colormap(n=256):
    """A colormap with the contour's hue ramp, blue for low values and red for high ones."""
    return ListedColormap(hue_colours(n), name="ghe_contour")


def contour_bands(ax, x, y, z, levels, transparency=0.5):
    """Fills the bands between iso-levels with the contour's colours.

    The first level's colour is blue and the last is red. A far field above every level (a cold
    plume in warmer ground) leaves the outside transparent and puts the coldest colour on the
    inside of the lowest level, as the application does.
    """
    levels = np.asarray(levels, dtype=float)
    n = len(levels)
    colours = hue_colours(n)
    far = z[0, 0]
    clear = (0.0, 0.0, 0.0, 0.0)
    if far > levels[0]:                      # cold trough
        bands = [colours[0]] + colours[1:] + [clear]
    else:
        bands = [clear] + colours[:-1] + [colours[-1]]
    bands = [c if len(c) == 4 else (*c, transparency) for c in bands]
    edges = np.concatenate([[-np.inf], levels, [np.inf]])
    finite = np.where(np.isfinite(edges), edges, np.sign(edges) * 1e9)
    return ax.contourf(x, y, z, levels=finite, colors=bands, antialiased=True)


def boreholes(ax, x, y, size=14):
    """The boreholes of the field, as dots."""
    ax.scatter(x, y, s=size, facecolor="black", edgecolor="white", linewidth=0.6, zorder=5)


def axis_titles(ax, x=None, y=None):
    """Sets the axis titles. Pass them as the panel words them: 'Time (h)', 'Temperature (°C)'."""
    if x is not None:
        ax.set_xlabel(x)
    if y is not None:
        ax.set_ylabel(y)


def mode_lines(ax, x, heating, cooling, marker="o"):
    """Two curves, one per mode, in the colours the panels give them: red for heating, blue for
    cooling, with the panels' legend."""
    ax.plot(x, heating, color=RED, marker=marker, markersize=3.5)
    ax.plot(x, cooling, color=BLUE, marker=marker, markersize=3.5)
    legend(ax, [(RED, "Heating mode"), (BLUE, "Cooling mode")])


def mode_bars(ax, labels, heating, cooling):
    """Grouped bars, one pair per label: heating in red, cooling in blue."""
    x = np.arange(len(labels))
    width = 0.38
    ax.bar(x - width / 2, heating, width, color=RED)
    ax.bar(x + width / 2, cooling, width, color=BLUE)
    ax.set_xticks(x, labels)
    ax.axhline(0, color=AXIS, linewidth=0.8)
    legend(ax, [(RED, "Heating mode"), (BLUE, "Cooling mode")])
