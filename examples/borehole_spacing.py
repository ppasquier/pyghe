"""Effect of the spacing between boreholes.

Keeps the twelve boreholes of the office building of demo_project.py on a 4 × 3 grid, varies
their spacing from 3 to 12 m, and plots the coldest entering fluid temperature of a 25-year
simulation and the length asked by the Sizing tool.

    python borehole_spacing.py [figure.png]
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
    spacings = np.arange(3.0, 12.1, 1.0)                 # m

    # -------------------------------------------------------------------------
    # One field per spacing, simulated and sized
    # -------------------------------------------------------------------------
    p = make_project()
    variants = []
    for spacing in spacings:
        q = p.copy()
        q.ground_heat_exchanger.coordinates = ga.Coordinates.rectangle(nx=4, ny=3, spacing=spacing)
        variants.append(q)

    coldest = [r.summary.minimum_eft for r in ga.run_many(variants, "simulate")]
    lengths = [r.governing_total_borehole_length for r in ga.run_many(variants, "size")]

    for spacing, temperature, length in zip(spacings, coldest, lengths):
        print(f"B = {spacing:4.1f} m  ->  minimum EFT {temperature:5.2f} °C, L = {length:5.0f} m")

    # -------------------------------------------------------------------------
    # Figure
    # -------------------------------------------------------------------------
    ghe.use()
    fig, (left, right) = plt.subplots(1, 2, figsize=(8.6, 3.0))
    left.plot(spacings, coldest, color=ghe.ORANGE, marker="o", markersize=3.5)
    ghe.axis_titles(left, "Spacing (m)", "Minimum EFT (°C)")
    right.plot(spacings, lengths, color=ghe.HEATING, marker="o", markersize=3.5)
    ghe.axis_titles(right, "Spacing (m)", "Total borehole length (m)")
    if figure:
        fig.savefig(figure)
    else:
        plt.show()


if __name__ == "__main__":
    main(*sys.argv[1:])
