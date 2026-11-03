"""Uncertainty of the ground thermal conductivity.

Sizes the office building of demo_project.py for ground thermal conductivities from 1.5 to
3.5 W/m·K, and plots the total borehole length each mode requires.

    python conductivity_uncertainty.py [figure.png]
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
    conductivities = np.arange(1.5, 3.51, 0.25)          # W/m·K

    # -------------------------------------------------------------------------
    # One sizing per conductivity, run in parallel
    # -------------------------------------------------------------------------
    p = make_project()
    study = ga.sweep(p, {"ground_heat_exchanger.ground_thermal_conductivity": conductivities}, "size")

    for k, length in zip(conductivities, study["governing_total_borehole_length"]):
        print(f"ks = {k:.2f} W/m·K  ->  L = {length:6.0f} m")

    # -------------------------------------------------------------------------
    # Figure
    # -------------------------------------------------------------------------
    ghe.use()
    fig, ax = ghe.figure(width=7.0)
    ghe.mode_lines(ax, conductivities, study["total_borehole_length_heating"],
                   study["total_borehole_length_cooling"])
    ghe.axis_titles(ax, "Ground thermal conductivity (W/m·K)", "Total borehole length (m)")
    if figure:
        fig.savefig(figure)
    else:
        plt.show()


if __name__ == "__main__":
    main(*sys.argv[1:])
