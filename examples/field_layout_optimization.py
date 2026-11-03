"""Optimization of the borehole positions.

Places the twelve boreholes of the office building of demo_project.py anywhere in a rectangular lot,
at least 4 m apart, so that the coldest entering fluid temperature of a 25-year simulation is as
warm as possible. The search is a plain evolutionary one: each generation perturbs the best layout
found so far in several ways, and run_many simulates the candidates together.

    python field_layout_optimization.py [figure.png]
"""

import sys
import time

import matplotlib.pyplot as plt
import numpy as np

import pyghe as ga
import ghestyle as ghe
from demo_project import make_project


def feasible(xy, lot, minimum_distance):
    """Every head is inside the lot and no two heads are closer than the minimum distance."""
    inside = (xy[:, 0] >= 0).all() and (xy[:, 0] <= lot[0]).all() and (xy[:, 1] >= 0).all() and (xy[:, 1] <= lot[1]).all()
    d = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1))
    return inside and (d[np.triu_indices(len(xy), 1)] >= minimum_distance).all()


def main(figure=None):
    # -------------------------------------------------------------------------
    # Parameters
    # -------------------------------------------------------------------------
    lot = (30.0, 20.0)                                   # m, easting × northing
    minimum_distance = 4.0                               # m between two boreholes
    generations, children = 20, 8
    rng = np.random.default_rng(1)

    p = make_project()
    start = ga.Coordinates.rectangle(nx=4, ny=3, spacing=6.0)
    best = np.column_stack([start.x, start.y]) + [6.0, 4.0]       # the 6 m grid, centred in the lot

    def variant(xy):
        q = p.copy()
        q.ground_heat_exchanger.coordinates = ga.Coordinates.from_points(xy)
        return q

    # -------------------------------------------------------------------------
    # Evolutionary search: the step shrinks as the layout improves
    # -------------------------------------------------------------------------
    best_eft = variant(best).simulate().summary.minimum_eft
    history = [best_eft]
    print(f"6 m grid: minimum EFT {best_eft:5.2f} °C")
    first = best.copy()
    step = 4.0                                           # m, standard deviation of a move
    t0 = time.time()
    for generation in range(generations):
        candidates = []
        while len(candidates) < children:
            xy = best.copy()
            moved = rng.random(len(xy)) < 0.35           # each borehole moves with probability 0.35
            moved[rng.integers(len(xy))] = True
            xy[moved] += rng.normal(0, step, (moved.sum(), 2))
            if feasible(xy, lot, minimum_distance):
                candidates.append(xy)
        results = ga.run_many([variant(xy) for xy in candidates], "simulate")
        temperatures = [r.summary.minimum_eft for r in results]
        k = int(np.argmax(temperatures))
        if temperatures[k] > best_eft:
            best, best_eft = candidates[k], temperatures[k]
        else:
            step *= 0.8
        history.append(best_eft)
        print(f"generation {generation + 1:2d}: minimum EFT {best_eft:5.2f} °C")
    print(f"{generations * children} simulations in {time.time() - t0:.0f} s")

    # -------------------------------------------------------------------------
    # Figure
    # -------------------------------------------------------------------------
    ghe.use()
    fig, (left, right) = plt.subplots(1, 2, figsize=(8.6, 3.2), gridspec_kw={"width_ratios": [1.5, 1]})
    left.add_patch(plt.Rectangle((0, 0), *lot, fill=False, edgecolor="0.6", linestyle="--"))
    left.scatter(*first.T, s=28, facecolor="none", edgecolor=ghe.BLUE, label="6 m grid")
    left.scatter(*best.T, s=28, color=ghe.ORANGE, label="optimized")
    left.set_aspect("equal")
    ghe.axis_titles(left, "Easting (m)", "Northing (m)")
    left.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=2)
    right.plot(range(generations + 1), history, color=ghe.ORANGE, marker="o", markersize=3.5)
    ghe.axis_titles(right, "Generation", "Minimum EFT (°C)")
    if figure:
        fig.savefig(figure, bbox_inches="tight")
    else:
        plt.show()


if __name__ == "__main__":
    main(*sys.argv[1:])
