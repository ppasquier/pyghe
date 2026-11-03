"""Room left in the field for a growing building.

Scales the heating, cooling and domestic hot water demands of the office building of
demo_project.py by up to 40 %, simulates each case over 25 years, and plots the coldest and the
warmest entering fluid temperature against the two temperature limits.

    python building_growth.py [figure.png]
"""

import sys

import matplotlib.pyplot as plt
import numpy as np

import pyghe as ga
import ghestyle as ghe
from demo_project import make_project


def main(figure=None):
    # -------------------------------------------------------------------------
    # Parameters
    # -------------------------------------------------------------------------
    growths = np.arange(1.0, 1.41, 0.05)                 # factor applied to every demand

    # -------------------------------------------------------------------------
    # One project per growth factor
    # -------------------------------------------------------------------------
    p = make_project()
    loads = p.building_loads
    variants = []
    for growth in growths:
        q = p.copy()
        q.building_loads = ga.HourlyBuildingLoadsSeparate(
            cooling_demand=loads.cooling_demand * growth,
            heating_demand=loads.heating_demand * growth,
            dhw_demand=loads.dhw_demand * growth)
        variants.append(q)

    results = ga.run_many(variants, "simulate")
    coldest = [r.summary.minimum_eft for r in results]
    warmest = [r.summary.maximum_eft for r in results]
    limit = p.heat_pump_performance.temperature_limit

    for growth, low, high in zip(growths, coldest, warmest):
        print(f"loads x{growth:.2f}  ->  EFT from {low:5.2f} to {high:5.2f} °C")

    # -------------------------------------------------------------------------
    # Figure
    # -------------------------------------------------------------------------
    ghe.use()
    fig, ax = ghe.figure(width=7.0)
    ax.plot(100 * (growths - 1), coldest, color=ghe.HEATING, marker="o", markersize=3.5)
    ax.plot(100 * (growths - 1), warmest, color=ghe.COOLING, marker="o", markersize=3.5)
    ax.axhline(limit.heating, color=ghe.HEATING, linestyle="--")
    ax.axhline(limit.cooling, color=ghe.COOLING, linestyle="--")
    ghe.legend(ax, [(ghe.HEATING, "Minimum EFT"), (ghe.COOLING, "Maximum EFT")])
    ghe.axis_titles(ax, "Growth of the loads (%)", "Temperature (°C)")
    if figure:
        fig.savefig(figure)
    else:
        plt.show()


if __name__ == "__main__":
    main(*sys.argv[1:])
