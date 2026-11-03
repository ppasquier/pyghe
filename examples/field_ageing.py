"""Long-term evolution of the entering fluid temperature.

Simulates the office building of demo_project.py over 50 years and plots, for each year, the
coldest and the warmest hour and the yearly mean of the entering fluid temperature.

    python field_ageing.py [figure.png]
"""

import sys

import matplotlib.pyplot as plt
import numpy as np

import ghestyle as ghe
from demo_project import make_project


def main(figure=None):
    # -------------------------------------------------------------------------
    # Parameters
    # -------------------------------------------------------------------------
    years = 50

    # -------------------------------------------------------------------------
    # Simulation, cut into years
    # -------------------------------------------------------------------------
    p = make_project()
    p.simulation_duration = years
    eft = p.simulate().eft.reshape(years, 8760)
    coldest, mean, warmest = eft.min(axis=1), eft.mean(axis=1), eft.max(axis=1)

    for year in (1, 5, 10, 25, 50):
        print(f"year {year:2d}  ->  EFT from {coldest[year - 1]:5.2f} to {warmest[year - 1]:5.2f} °C")

    # -------------------------------------------------------------------------
    # Figure
    # -------------------------------------------------------------------------
    ghe.use()
    fig, ax = ghe.figure(width=7.0)
    year = np.arange(1, years + 1)
    ax.plot(year, warmest, color=ghe.COOLING)
    ax.plot(year, mean, color=ghe.BLACK)
    ax.plot(year, coldest, color=ghe.HEATING)
    ghe.legend(ax, [(ghe.COOLING, "Warmest hour"), (ghe.BLACK, "Yearly mean"),
                    (ghe.HEATING, "Coldest hour")])
    ghe.axis_titles(ax, "Year", "Entering fluid temperature (°C)")
    if figure:
        fig.savefig(figure)
    else:
        plt.show()


if __name__ == "__main__":
    main(*sys.argv[1:])
