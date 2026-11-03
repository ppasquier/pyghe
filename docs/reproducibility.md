# Reproducibility

A result that goes into a paper, a thesis or a report has to be obtainable again, and each
result carries what is needed to do that.

## What a result keeps

A result holds the case that produced it and the versions of the software that computed it:

```python
result = p.simulate()
print(result.meta)
print(sorted(result.case))
```

```text
{'command': 'ghe simulation', 'interfaceVersion': '1.9', 'program': 'AnalysisSuite-cli', 'version': '3.0.1', 'threads': None}
['borehole', 'field', 'fluid', 'ground', 'heatPumps', 'loads', 'options', 'simulation', 'sizing', 'system', 'units']
```

The case is the executable's JSON, with its own names.
`result.save(path)` writes the result and its case together, and `ga.load_result(path)` reads both
back. `ga.__version__` is the version of the package.

To redo a study you need the case or the `.ghe`, the version of Analysis Suite recorded in
`meta`, and the thread count.

## How closely a result is reproduced

**Through Python or through the executable:** the results are identical. The package does no
arithmetic of its own, so a case run directly by `AnalysisSuite-cli` gives the same numbers, bit
for bit.

**Against GHE Analysis:** the results agree within the convergence criterion. The application
starts each simulation from its previous solution and the executable starts from scratch. Both
stop when the entering fluid temperature changes by less than 10⁻³ K and the ground load by less
than 0.1 kW between two iterations, so they agree to that tolerance and not to the last digit. A
difference of a thousandth of a kelvin between a script and the application is expected.

**Between thread counts:** only the last bits differ, about 2·10⁻¹² K on the entering fluid
temperature between 1 and 20 threads. With `threads=1`, two runs are identical to the bit.

No value is converted on its way to the kernel: the number you give is the number the kernel uses.

[Citing](citing.md) says how to cite the package and the methods behind it.
