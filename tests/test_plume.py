"""Thermal plumes, 2D and 3D. Needs the executable."""

import json
import os
import subprocess
import warnings

import numpy as np
import pytest

import pyghe as ga
from pyghe._cli import plain


def direct(cli, command, case):
    env = dict(os.environ, OMP_NUM_THREADS="1")
    out = subprocess.run([cli, *command.split(), "--compact"], input=json.dumps(case).encode(),
                         capture_output=True, env=env)
    return json.loads(out.stdout)


def bilinear(x, y, values, xq, yq):
    """values[iy, ix] on the axes x, y, read at (xq, yq) inside the grid."""
    ix = np.clip(np.searchsorted(x, xq) - 1, 0, x.size - 2)
    iy = np.clip(np.searchsorted(y, yq) - 1, 0, y.size - 2)
    tx = (xq - x[ix]) / (x[ix + 1] - x[ix])
    ty = (yq - y[iy]) / (y[iy + 1] - y[iy])
    return ((1 - tx) * (1 - ty) * values[iy, ix] + tx * (1 - ty) * values[iy, ix + 1]
            + (1 - tx) * ty * values[iy + 1, ix] + tx * ty * values[iy + 1, ix + 1])


@pytest.mark.parametrize("method, command", [("compute_thermal_plume_2d", "ghe plume2d"),
                                             ("compute_thermal_plume_3d", "ghe plume3d")])
def test_identical_to_a_direct_run(cli, project, method, command):
    r = getattr(project, method)(8760, threads=1)
    assert r.converged and r.simulation_converged
    assert plain(r.raw) == direct(cli, command, r.case)["result"]


def test_plume_2d_grid(cli, project):
    r = project.compute_thermal_plume_2d(8760)
    assert r.values.shape == (r.y.size, r.x.size)
    assert np.all(np.diff(r.x) > 0) and np.all(np.diff(r.y) > 0)
    assert r.x.min() == pytest.approx(-300.0) and r.x.max() == pytest.approx(306.0)
    assert r.reading == "Temp. perturbation" and r.time == 8760 and r.unit == "K"
    # Far from the field the ground is undisturbed.
    assert np.abs(r.values[[0, -1], :]).max() < 0.01 and np.abs(r.values[:, [0, -1]]).max() < 0.01


def test_plume_2d_ground_temperature_is_tg_plus_delta_t(cli, project):
    dt = project.compute_thermal_plume_2d(4000)
    t = project.compute_thermal_plume_2d(4000, reading="Ground Temp.")
    assert t.unit == "°C"
    assert np.array_equal(t.values, dt.values + dt.undisturbed_ground_temperature)


def test_plume_2d_square_field_is_symmetric(cli, project):
    """The field of a square field without groundwater is symmetric about the field's centre;
    the grid need not be (its union of borehole grids is thinned at 0.25 m), so the field is
    read at mirrored points."""
    r = project.compute_thermal_plume_2d(8760)
    angle = np.linspace(0, 2 * np.pi, 37)
    radius = np.repeat([8.0, 15.0, 30.0, 60.0], angle.size)
    xq = 3.0 + radius * np.cos(np.tile(angle, 4))
    yq = 3.0 + radius * np.sin(np.tile(angle, 4))
    v = bilinear(r.x, r.y, r.values, xq, yq)
    peak = np.abs(r.values).max()
    assert np.abs(v - bilinear(r.x, r.y, r.values, 6.0 - xq, yq)).max() < 0.01 * peak
    assert np.abs(v - bilinear(r.x, r.y, r.values, xq, 6.0 - yq)).max() < 0.01 * peak


def test_plume_2d_follows_the_groundwater(cli, project):
    still = project.compute_thermal_plume_2d(4000)
    project.ground_heat_exchanger.groundwater_flow = 1e-6
    project.ground_heat_exchanger.groundwater_flow_direction = 90  # towards the east
    moving = project.compute_thermal_plume_2d(4000)
    xx = np.broadcast_to(still.x, still.values.shape)
    weight = lambda r: np.abs(r.values)
    centroid = lambda r: float((weight(r) * xx).sum() / weight(r).sum())
    assert centroid(still) == pytest.approx(3.0, abs=0.5)
    assert centroid(moving) > centroid(still) + 2


def test_plume_3d_grid_and_reading(cli, project):
    dt = project.compute_thermal_plume_3d(8760)
    assert dt.values.shape == (dt.z.size, dt.y.size, dt.x.size)
    assert np.all(np.diff(dt.z) > 0) and dt.z[0] >= 0
    ghe = project.ground_heat_exchanger
    assert dt.z.max() > ghe.burial_depth + ghe.active_length
    t = project.compute_thermal_plume_3d(8760, reading="Ground Temp.")
    gradient = 1e-3 * ghe.geothermal_heat_flux / ghe.ground_thermal_conductivity
    profile = dt.undisturbed_ground_temperature + gradient * (dt.z - (ghe.burial_depth + ghe.active_length / 2))
    assert np.allclose(t.values, dt.values + profile[:, None, None], rtol=0, atol=1e-12)


def test_plume_3d_grid_follows_the_contours(cli, project):
    default = project.compute_thermal_plume_3d(8760)
    wide = project.compute_thermal_plume_3d(8760, contour_min=0.02, contour_max=1.0)
    assert wide.x.max() - wide.x.min() > default.x.max() - default.x.min()
    tg = default.undisturbed_ground_temperature
    same = project.compute_thermal_plume_3d(8760, reading="Ground Temp.", contour_min=tg + 0.1,
                                            contour_max=tg + 1.0)
    assert np.array_equal(same.x, default.x) and np.array_equal(same.z, default.z)


def test_plume_3d_mid_depth_agrees_with_the_2d(cli, project):
    """A 300 m borehole after one year: the vertical factor is 1 at mid-depth, and the 3D section
    there is the 2D plume (in the application, within 0.82 % of the peak at r > 1 m)."""
    ghe = project.ground_heat_exchanger
    ghe.active_length = 300
    ghe.burial_depth = 2
    project.gshp_system.flow_rate_of_pump_a = (96, 96)
    p2, p3 = project.compute_thermal_plume_2d(8760), project.compute_thermal_plume_3d(8760)
    z_mid = ghe.burial_depth + ghe.active_length / 2
    k = np.clip(np.searchsorted(p3.z, z_mid) - 1, 0, p3.z.size - 2)
    w = (z_mid - p3.z[k]) / (p3.z[k + 1] - p3.z[k])
    section = (1 - w) * p3.values[k] + w * p3.values[k + 1]
    xx, yy = np.meshgrid(p3.x, p3.y)
    heads = ga.Coordinates.rectangle(nx=2, ny=2, spacing=6.0)
    far = np.min([np.hypot(xx - hx, yy - hy) for hx, hy in zip(heads.x, heads.y)], axis=0) > 1.0
    two_d = bilinear(p2.x, p2.y, p2.values, xx[far], yy[far])
    peak = np.abs(p2.values).max()
    assert np.abs(section[far] - two_d).max() < 0.01 * peak


def test_inclined_boreholes_refused_in_3d(cli, project):
    project.ground_heat_exchanger.coordinates = ga.Coordinates.from_points(
        [(0, 0), (20, 0)], az=[0, 180], dip=[80, 80])
    with pytest.raises(ga.InvalidInputError, match="vertical boreholes only"):
        project.compute_thermal_plume_3d(8760)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert project.compute_thermal_plume_2d(8760).converged


def test_time_beyond_the_simulation(cli, project):
    project.simulation_duration = 1
    with pytest.raises(ga.InvalidInputError, match=r"compute_thermal_plume \(time\).*8760"):
        project.compute_thermal_plume_2d(8761)


def test_arguments_checked_before_running(project):
    with pytest.raises(ga.InvalidInputError, match="reading"):
        project.compute_thermal_plume_2d(10, reading="deltaT")
    with pytest.raises(ga.InvalidInputError, match="time"):
        project.compute_thermal_plume_2d(0)
    with pytest.raises(ga.InvalidInputError, match="both"):
        project.compute_thermal_plume_3d(10, contour_min=0.1)
