"""The charts of GHE Analysis, redrawn from the results of the package.

One function per chart of the Charts panel (entering fluid temperature, thermal loads, ground
load, COP, capacity, temperature difference, effective resistance, g-function), plus the Borehole
designer's stacked resistances and the thermal contour of the plumes. Each takes a project and a
result and returns a matplotlib figure, drawn with the application's colours, axis titles and
legends (see ghestyle.py for where they come from).

A series asked from `simulate` must have been requested: the notebooks ask for the ones they draw.
"""

import numpy as np

import ghestyle as ghe

# Series each chart reads, for `p.simulate(series=...)`.
SERIES = {
    "eft": ["entering_fluid_temperature"],
    "loads": ["building_load", "heat_pump_load", "auxiliary_load"],
    "ground_load": ["ground_load", "heat_pump_load"],
    "cop": ["effective_cop", "heat_pump_load"],
    "capacity": ["effective_capacity"],
    "delta_t": ["fluid_temperature_difference"],
    "rb": ["effective_borehole_resistance"],
}
ALL_CHARTS = sorted({name for names in SERIES.values() for name in names})


def _hours(n):
    return np.arange(1, n + 1)


def _window(n, start, stop):
    stop = n if stop is None else stop
    return _hours(n)[start:stop], slice(start, stop)


def _style_time_axis(ax, t):
    ax.set_xlim(t[0] - 0.01 * (t[-1] - t[0]), t[-1])
    ghe.axis_titles(ax, x="Time (h)")


def eft_chart(p, r, start=0, stop=None, size=None):
    """Chart 0, entering fluid temperature: hourly (orange), daily mean (black), and the two
    temperature limits of the heat pumps (red in heating, blue in cooling)."""
    eft = r.hourly.entering_fluid_temperature
    t, s = _window(len(eft), start, stop)
    limit = p.heat_pump_performance.temperature_limit
    fig, ax = ghe.figure(*(size or ()))
    ax.plot([t[0], t[-1]], [limit.cooling] * 2, color=ghe.BLUE)
    ax.plot([t[0], t[-1]], [limit.heating] * 2, color=ghe.RED)
    ax.plot(t, eft[s], color=ghe.ORANGE, linewidth=0.5 if len(t) > 20000 else 1.0)
    days = np.arange(len(r.daily_eft)) * 24 + 12.5
    inside = (days >= t[0]) & (days <= t[-1])
    ax.plot(days[inside], r.daily_eft[inside], color=ghe.BLACK, linewidth=0.8)
    _style_time_axis(ax, t)
    ghe.axis_titles(ax, y="Temperature (°C)")
    ghe.legend(ax, [(ghe.RED, "Heating T$_{Lim}$"), (ghe.BLUE, "Cooling T$_{Lim}$"),
                    (ghe.ORANGE, "Hourly EFT"), (ghe.BLACK, "Daily EFT")])
    return fig


def thermal_load_chart(r, start=0, stop=None, size=None):
    """Chart 1, demand coverage: the building demand (orange in heating, green in cooling), the
    heat pumps plus the auxiliary (light red and light blue) and the heat pumps alone (red, blue)."""
    h = r.hourly
    t, s = _window(len(h.building_load), start, stop)
    heat_pump = h.heat_pump_load[s]
    fig, ax = ghe.figure(*(size or ()))
    ghe.signed_line(ax, t, h.building_load[s], ghe.ORANGE, ghe.GREEN)
    ghe.signed_line(ax, t, heat_pump + h.auxiliary_load[s], ghe.RED2, ghe.BLUE2)
    ghe.signed_line(ax, t, heat_pump, ghe.RED, ghe.BLUE)
    _style_time_axis(ax, t)
    ghe.axis_titles(ax, y="Thermal load (kW)")
    ghe.legend(ax, [(ghe.ORANGE, "Heating - Demand"), (ghe.RED2, "Heating - Auxiliary"),
                    (ghe.RED, "Heating - Heat pump"), (ghe.BLUE, "Cooling - Heat pump"),
                    (ghe.BLUE2, "Cooling - Auxiliary"), (ghe.GREEN, "Cooling - Demand")])
    return fig


def ground_load_chart(r, start=0, stop=None, size=None):
    """Chart 2, ground load: positive (blue) when heat is injected, negative (red) when it is
    extracted."""
    q = r.hourly.ground_load
    t, s = _window(len(q), start, stop)
    fig, ax = ghe.figure(*(size or ()))
    ghe.signed_line(ax, t, q[s], ghe.BLUE, ghe.RED)
    _style_time_axis(ax, t)
    ghe.axis_titles(ax, y="Ground load (kW)")
    ghe.legend(ax, [(ghe.RED, "Heating load"), (ghe.BLUE, "Cooling load")])
    return fig


def cop_chart(r, start=0, stop=None, size=None):
    """Chart 3, effective COP, drawn up in heating (red) and down in cooling (blue)."""
    h = r.hourly
    cop = np.where(h.heat_pump_load >= 0, h.effective_cop, -h.effective_cop)
    t, s = _window(len(cop), start, stop)
    fig, ax = ghe.figure(*(size or ()))
    ghe.signed_line(ax, t, cop[s], ghe.RED, ghe.BLUE)
    _style_time_axis(ax, t)
    ghe.axis_titles(ax, y="COP (-)")
    ghe.legend(ax, [(ghe.RED, "Heating mode"), (ghe.BLUE, "Cooling mode")])
    return fig


def capacity_chart(r, start=0, stop=None, size=None):
    """Chart 4, effective capacity of the heat pumps. The kernel's sign is the opposite of the
    chart's, as in the application, which plots minus the capacity."""
    q = -r.hourly.effective_capacity
    t, s = _window(len(q), start, stop)
    fig, ax = ghe.figure(*(size or ()))
    ghe.signed_line(ax, t, q[s], ghe.RED, ghe.BLUE)
    _style_time_axis(ax, t)
    ghe.axis_titles(ax, y="Q$_{HP}$ (kW)")
    ghe.legend(ax, [(ghe.RED, "Heating mode"), (ghe.BLUE, "Cooling mode")])
    return fig


def delta_t_chart(r, start=0, stop=None, size=None):
    """Chart 5, temperature difference between the entering and the leaving fluid."""
    d = r.hourly.fluid_temperature_difference
    t, s = _window(len(d), start, stop)
    fig, ax = ghe.figure(*(size or ()))
    ghe.signed_line(ax, t, d[s], ghe.BLUE, ghe.RED)
    _style_time_axis(ax, t)
    ghe.axis_titles(ax, y="ΔT (K)")
    ghe.legend(ax, [(ghe.RED, "Heating mode"), (ghe.BLUE, "Cooling mode")])
    return fig


def rb_chart(r, start=0, stop=None, size=None):
    """Chart 6, effective borehole resistance Rb* through the run."""
    rb = r.hourly.effective_borehole_resistance
    t, s = _window(len(rb), start, stop)
    fig, ax = ghe.figure(*(size or ()))
    ax.plot(t, rb[s], color=ghe.ORANGE, linewidth=1.0)
    _style_time_axis(ax, t)
    ghe.axis_titles(ax, y="Rb$^{*}$ (mK/W)")
    return fig


def gfunction_chart(gf, size=None):
    """Chart 7, the g-function against ln(t), t in hours."""
    hours = gf.time / 3600.0
    keep = hours > 0
    fig, ax = ghe.figure(*(size or ()))
    ax.plot(np.log(hours[keep]), gf.values[keep], color=ghe.ORANGE, linewidth=1.5)
    ghe.axis_titles(ax, x="ln(t) (h)", y="g-function (mK/W)")
    return fig


_PIPES = {"SingleULoop": 2, "DoubleULoopA": 4, "DoubleULoopD": 4}


def resistance_chart(p, rb, size=None):
    """The Borehole designer's chart: effective resistance Rb* against the flow per borehole at the
    heating temperature limit, stacked in the four resistances it is made of.

    Bottom to top, as the panel draws them: advective R_eta (red), grout R_g (orange), pipe R_p
    (green) and fluid R_f (blue). rb must come from `compute_borehole_resistance(include_grid=True)`.
    The package returns Rb, Rb*, Rf and Rp; the panel's other two are formed from them, as it does:
    R_eta = Rb* - Rb, and R_g = Rb - (Rp + Rf) / npipe.
    """
    kind = type(p.borehole_resistance).__name__
    if kind not in _PIPES:
        raise NotImplementedError("the stacked chart is drawn for U-loops")
    npipe = _PIPES[kind]
    grid = rb.grid
    flow = np.asarray(grid.flow_rate_per_borehole)
    temperature = np.asarray(grid.temperature)
    at_limit = p.heat_pump_performance.temperature_limit.heating

    def along_flow(table):
        table = np.asarray(table)
        return np.array([np.interp(at_limit, temperature, table[:, j]) for j in range(table.shape[1])])

    rf = along_flow(grid.convective_resistance)
    rb_eq = along_flow(grid.equivalent_borehole_resistance)
    rb_eff = along_flow(grid.effective_borehole_resistance)
    rp = rb.pipe_resistance / npipe
    advective = rb_eff - rb_eq
    grout = rb_eq - (rb.pipe_resistance + rf) / npipe
    top1, top2, top3, top4 = advective, advective + grout, advective + grout + rp, rb_eff

    low, high = (10, 60) if npipe == 2 else (10, 120)
    keep = (flow >= low) & (flow <= high)
    x = flow[keep]
    fig, ax = ghe.figure(*(size or ()))
    bands = [(0 * x, top1[keep], ghe.RED), (top1[keep], top2[keep], ghe.ORANGE),
             (top2[keep], top3[keep], ghe.GREEN), (top3[keep], top4[keep], ghe.BLUE)]
    for lower, upper, colour in bands:
        ax.fill_between(x, lower, upper, color=colour, alpha=0.65, linewidth=0)
        ax.plot(x, upper, color=colour, linewidth=1.0)
    per_borehole = p.gshp_system.flow_rate_of_pump_a.heating / len(p.ground_heat_exchanger.coordinates)
    ax.axvline(per_borehole, color=ghe.BLACK, linewidth=0.8, linestyle=(0, (4, 3)))
    ax.set_xlim(low, high)
    ax.set_ylim(0, 0.6)
    ghe.axis_titles(ax, x="Flowrate per borehole (L/min)",
                    y="Effective borehole resistance - R$_{b}$$^{*}$ (mK/W)")
    ghe.legend(ax, [(ghe.BLUE, "Fluid - R$_{f}$"), (ghe.GREEN, "Pipe - R$_{p}$"),
                    (ghe.ORANGE, "Grout - R$_{g}$"), (ghe.RED, "Advective - R$_{η}$")])
    return fig


def contour_levels(values, low=0.1, high=1.0, count=10):
    """The panel's default levels for a perturbation: ten values from 0.1 to 1.0 K in magnitude, on
    the side the plume lies, so that a cold plume is contoured at -1.0 ... -0.1 K."""
    cold = abs(np.nanmin(values)) > abs(np.nanmax(values))
    magnitudes = np.linspace(low, high, count)
    return -magnitudes[::-1] if cold else magnitudes


def _level_legend(ax, levels):
    colours = ghe.hue_colours(len(levels))
    entries = [(c, f"{v:+.1f} K") for c, v in zip(colours, levels)]
    ghe.legend(ax, entries)


def plume2d_panel(ax, p, plume, levels=None, margin=20.0, zoom=True):
    """One 2D plume on `ax`: the contour's bands, the boreholes, equal axes. With zoom=True the axes
    close in on the plume; give zoom=False to set the limits yourself, to compare several times."""
    z = np.asarray(plume.values)
    levels = contour_levels(z) if levels is None else levels
    ghe.contour_bands(ax, plume.x, plume.y, z, levels)
    c = p.ground_heat_exchanger.coordinates
    ghe.boreholes(ax, c.x, c.y)
    inside = np.abs(z) >= abs(levels).min()
    if zoom and inside.any():
        iy, ix = np.where(inside)
        ax.set_xlim(plume.x[ix.min()] - margin, plume.x[ix.max()] + margin)
        ax.set_ylim(plume.y[iy.min()] - margin, plume.y[iy.max()] + margin)
    ax.set_aspect("equal")
    ghe.axis_titles(ax, x="x (m)", y="y (m)")
    return levels


def plume2d_chart(p, plume, size=(6.4, 5.2)):
    """The 2D thermal contour of the Ground heat exchanger panel, at one time."""
    fig, ax = ghe.figure(*size)
    levels = plume2d_panel(ax, p, plume)
    _level_legend(ax, levels)
    return fig


def plume3d_section(p, plume, size=(7.6, 3.6)):
    """A vertical section through the middle of the 3D plume (x against depth), drawn with the
    contour's colours."""
    z = np.asarray(plume.values)
    middle = z.shape[1] // 2
    section = z[:, middle, :]
    levels = contour_levels(section)
    fig, ax = ghe.figure(*size)
    ghe.contour_bands(ax, plume.x, plume.z, section, levels)
    ax.invert_yaxis()
    ghe.axis_titles(ax, x="x (m)", y="Depth (m)")
    _level_legend(ax, levels)
    return fig
