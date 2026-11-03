# Examples

The scripts and notebooks of the `examples` folder all work on the same project: a small office
building heated and cooled by four heat pumps on a field of twelve boreholes, built by
`make_project()` in `demo_project.py`. Their figures use the colours and the wording of the
application's charts (`ghestyle.py`).

The scripts run from the `examples` folder. Given a file name, a script saves its figure instead of
showing it:

```console
cd examples
python field_ageing.py
```

```{toctree}
:maxdepth: 1
:caption: Scripts

conductivity_uncertainty
building_growth
borehole_spacing
field_ageing
field_layout_optimization
```

Each script also exists as a notebook (04 to 08). The first three notebooks go further, with about
thirty figures. They are shown here with the outputs saved in them.

```{toctree}
:maxdepth: 1
:caption: Notebooks

../notebooks/01_simulation
../notebooks/02_sizing
../notebooks/03_parametric_studies
../notebooks/04_conductivity_uncertainty
../notebooks/05_building_growth
../notebooks/06_borehole_spacing
../notebooks/07_field_ageing
../notebooks/08_field_layout_optimization
```
