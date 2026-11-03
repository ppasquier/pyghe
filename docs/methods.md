# Methods

Each computation of the package is done by the GHE Analysis kernel. For each one, this page gives
the method the kernel uses and where it was published. Most of these methods were developed at
Polytechnique Montréal by Denis Marcotte, by my graduate students and by me. The others come from
colleagues whose work I rely on. The equations are in the papers.

## Fluid properties

`ga.fluid_properties()`, and every computation that needs the heat carrier fluid. The density,
specific heat capacity, thermal conductivity, viscosity and freezing temperature of water and of
its four antifreeze mixtures are the polynomial correlations of Melinder (2010), in temperature
and mass concentration.

## Borehole thermal resistance

`p.compute_borehole_resistance()`, and the resistances used by the simulation and the sizing.

The convective resistance inside the pipes comes from the Nusselt correlations for laminar,
transition and turbulent flow (Hausen, Gnielinski, Petukhov) as given in chapter 2 of
Lamarche (2023), chosen by the Reynolds number.

- **Single U-loop.** The local resistance Rb and the internal resistance Ra are given by the
  first-order multipole formulas (Bennet et al., 1987), in the explicit form of Javed & Spitler
  (2017, eq. 26).
- **Double U-loop**, adjacent or diagonal. The explicit multipole formulas of Claesson & Javed
  (2019).
- **Coaxial and standing column well.** The thermal network of Lamarche (2023, eq. 5.96 to 5.98).

The effective resistance Rb\* accounts for the heat exchanged between the downward and upward
flows along the borehole. It is the mean of its values under a uniform heat flux and under a
uniform wall temperature (Claesson & Javed, 2019).

The kernel computes these resistances once, on a grid of fluid temperatures and flow rates, and
interpolates in that grid during the simulation.

## g-function

`p.compute_gfunction()`, and the simulation and the sizing.

The response of one borehole to another is the moving finite line source with buried depth
(MFLSD) of Guo et al. (2020). It accounts for the depth of the top of the active length and, when
a Darcy velocity is given, for groundwater flow. For a field in which at least one borehole is
inclined, the kernel uses its inclined counterpart, as studied by Marcotte & Pasquier (2009).

The field's g-function is built under a uniform borehole wall temperature, in the sense of
Eskilson (1987), by the successive flux estimation of Pasquier & Marcotte (2013b), extended to
large fields by Nguyen & Pasquier (2021).

A standing column well has its own response, which includes the advection created by the bleed:
the analytical model of Nguyen et al. (2025), in the improved form of Jacques et al. (2025).

## Simulation

`p.simulate()`.

The temperature at the borehole wall is the convolution of the ground load with the g-function.
The kernel evaluates it in the spectral domain, for the whole simulation at once (Marcotte &
Pasquier, 2008; Pasquier et al., 2013). The variation of the fluid temperature along the borehole
is handled by the quasi-3D response model of Pasquier & Marcotte (2014).

The heat pumps, the ground and the fluid are coupled by a fixed-point iteration over all the
hours of the simulation. It stops when the entering fluid temperature changes by less than
10⁻³ K and the ground load by less than 0.1 kW between two iterations; it usually takes fewer
than 10 iterations. At part load, the COP is multiplied by the part-load factor
PLF = 1 − Cd (1 − PLR).

## Sizing

`p.size()`.

The total length comes from the three-pulse method of the ASHRAE handbook, a yearly, a monthly
and an hourly peak pulse (Kavanaugh & Rafferty, 1997), in the form revised by Ahmadfard & Bernier
(2018). The three response factors are read from the g-function of the field, computed as above.

## Thermal plumes

`p.compute_thermal_plume_2d()` and `p.compute_thermal_plume_3d()`.

The simulated hourly ground load is superposed on the response of each borehole. In 2D the
response is the moving infinite line source, taken at mid-length (Pasquier & Lamarche, 2022). In
3D it is the moving finite line source with buried depth (Guo et al., 2020).

## References

Ahmadfard, M., Bernier, M., 2018. Modifications to ASHRAE's sizing method for vertical ground heat
exchangers. *Science and Technology for the Built Environment* 24, 803–817.

Bennet, J., Claesson, J., Hellström, G., 1987. *Multipole method to compute the conductive heat
flows to and between pipes in a composite cylinder.* Notes on Heat Transfer 3, Department of
Building Technology and Mathematical Physics, University of Lund, Sweden.

Claesson, J., Javed, S., 2019. Explicit multipole formulas and thermal network models for
calculating thermal resistances of double U-pipe borehole heat exchangers. *Science and Technology
for the Built Environment* 25(8), 980–992.

Eskilson, P., 1987. *Thermal analysis of heat extraction boreholes.* Doctoral thesis, University
of Lund, Sweden.

Guo, Y., Hu, X., Banks, J., Liu, W.V., 2020. Considering buried depth in the moving finite line
source model for vertical borehole heat exchangers. *Energy and Buildings* 214, 109859.

Jacques, L., Pasquier, P., Nguyen, A., Beaudry, G., 2025. Improvement and experimental validation
of an analytical model for standing column wells operated with bleed. *Applied Thermal
Engineering* 279, 127620.

Javed, S., Spitler, J.D., 2017. Accuracy of borehole thermal resistance calculation methods for
grouted single U-tube ground heat exchangers. *Applied Energy* 187, 790–806.

Kavanaugh, S.P., Rafferty, K., 1997. *Ground-source heat pumps: design of geothermal systems for
commercial and institutional buildings.* ASHRAE, Atlanta.

Lamarche, L., 2023. *Fundamentals of geothermal heat pump systems: design and application.*
Springer, Cham.

Marcotte, D., Pasquier, P., 2008. Fast fluid and ground temperature computation for geothermal
ground-loop heat exchanger systems. *Geothermics* 37(6), 651–665.

Marcotte, D., Pasquier, P., 2009. The effect of borehole inclination on fluid and ground
temperature for GLHE systems. *Geothermics* 38(4), 392–398.

Melinder, Å., 2010. *Properties of secondary working fluids (secondary refrigerants or coolants,
heat transfer fluids) for indirect systems.* International Institute of Refrigeration, Paris.

Nguyen, A., Jacques, L., Pasquier, P., 2025. An easy-to-use analytical model for standing column
wells operating with bleed. *Applied Thermal Engineering* 258, 124543.

Nguyen, A., Pasquier, P., 2021. A successive flux estimation method for rapid g-function
construction of small to large-scale ground heat exchangers. *Renewable Energy* 165, 359–368.

Pasquier, P., Marcotte, D., 2013b. Efficient computation of heat flux signals to ensure the
reproduction of prescribed temperatures at several interacting heat sources. *Applied Thermal
Engineering* 59, 515–526.

Pasquier, P., Marcotte, D., 2014. Joint use of quasi-3D response model and spectral method to
simulate borehole heat exchanger. *Geothermics* 51, 281–299.

Pasquier, P., Lamarche, L., 2022. Analytic expressions for the moving infinite line source
model. *Geothermics* 103, 102413.

Pasquier, P., Marcotte, D., Bernier, M., Kummert, M., 2013. Simulation of ground-coupled heat pump
systems using a spectral approach. *Proceedings of the 13th Conference of IBPSA*, Chambéry,
France, 2691–2698.
