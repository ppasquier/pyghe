"""Building loads node. One class per 'Type of thermal load' of the interface; the year given is
repeated for every simulated year. Signs are those of the interface's load table: positive in
heating, negative in cooling."""

from ._base import HOURS_PER_YEAR, Node, node, param, series

_hourly = series(length=HOURS_PER_YEAR)
_monthly = series(length=12)


@node
class HourlyBuildingLoadsCombined(Node):
    """Hourly building loads - Combined: one column of 8760 hours, positive in heating,
    negative in cooling."""

    combined_demand: object = param("kW", _hourly)


@node
class HourlyBuildingLoadsSeparate(Node):
    """Hourly building loads - Separate: cooling, heating and domestic hot water demands over
    8760 hours. The building load is heating - |cooling|. Domestic hot water is served only in
    hours whose building load is not zero."""

    cooling_demand: object = param("kW", _hourly)
    heating_demand: object = param("kW", _hourly)
    dhw_demand: object = param("kW", _hourly)


@node
class HourlyGroundLoadsCombined(Node):
    """Hourly ground loads - Combined: a load applied to the ground directly, without heat pump
    (8760 hours), positive in heating (heat extracted from the ground), negative in cooling."""

    combined_demand: object = param("kW", _hourly)


@node
class MonthlyBuildingLoadsSeparate(Node):
    """Monthly building loads - Separate: twelve months of cooling, heating and domestic hot
    water demands, with the cooling and heating peaks. The kernel turns them into an hourly
    profile month by month; absolute values are used."""

    cooling_demand: object = param("kWh", _monthly)
    cooling_peak: object = param("kW", _monthly)
    heating_demand: object = param("kWh", _monthly)
    heating_peak: object = param("kW", _monthly)
    dhw_demand: object = param("kWh", _monthly)


BUILDING_LOAD_TYPES = (HourlyBuildingLoadsCombined, HourlyBuildingLoadsSeparate,
                       HourlyGroundLoadsCombined, MonthlyBuildingLoadsSeparate)
