import httpx
import logging
from collections import deque
from typing import Any
from ilo_fan_control.env import ILO_HOST, ILO_ADMIN_USER, ILO_ADMIN_PASSWORD

logger = logging.getLogger(__name__)

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FanReading:
    id: int
    name: str
    speed_percentage: int | None
    state: str
    health: str | None

    def __str__(self) -> str:
        speed = "unknown" if self.speed_percentage is None else f"{self.speed_percentage}%"

        return (
            f"FanReading("
            f"id={self.id}, "
            f"name={self.name!r}, "
            f"speed={speed}, "
            f"state={self.state}, "
            f"health={self.health or 'unknown'}"
            f")"
        )


@dataclass(frozen=True, slots=True)
class TemperatureReading:
    id: int
    name: str
    temperature_celsius: int | None
    physical_context: str | None
    state: str
    health: str | None
    critical_threshold_celsius: int | None
    fatal_threshold_celsius: int | None

    def __str__(self) -> str:
        temperature = (
            "unknown" if self.temperature_celsius is None else f"{self.temperature_celsius}°C"
        )

        return (
            f"TemperatureReading("
            f"id={self.id}, "
            f"name={self.name!r}, "
            f"temperature={temperature}, "
            f"context={self.physical_context or 'unknown'}, "
            f"state={self.state}, "
            f"health={self.health or 'unknown'}"
            f")"
        )


@dataclass(frozen=True, slots=True)
class ThermalData:
    fans: list[FanReading]
    temperatures: list[TemperatureReading]

    def get_fans(self, include_disabled: bool = False) -> list[FanReading]:
        """Get the list of Fans readings from iLO results.

        Args:
            include_disabled (bool, optional): Specifies wether to also get the disabled Fans. Defaults to False.

        Returns:
            list[FanReading]: List with the Fans readings.
        """

        if include_disabled:
            return self.fans.copy()

        return [fan for fan in self.fans if fan.state == "Enabled"]

    def get_temperatures(self, include_disabled: bool = False) -> list[TemperatureReading]:
        """Get the list of Temps readings from iLO results.

        Args:
            include_disabled (bool, optional): Specifies wether to also get the disabled Temp sensors. Defaults to False.

        Returns:
            list[TemperatureReading]: List with the Temps readings.
        """

        if include_disabled:
            return self.temperatures.copy()

        return [temp for temp in self.temperatures if temp.state == "Enabled"]

    def __str__(self) -> str:
        fan_entries = "\n".join(f"    {fan}" for fan in self.fans)

        temperature_entries = "\n".join(f"    {temperature}" for temperature in self.temperatures)

        return (
            "ThermalData[\n"
            "  Fans[\n"
            f"{fan_entries}\n"
            "  ]\n"
            "  Temperatures[\n"
            f"{temperature_entries}\n"
            "  ]\n"
            "]"
        )


@dataclass(frozen=True, slots=True)
class PowerSupplyReading:
    id: int
    output_watts: int | None
    capacity_watts: int | None
    input_voltage: int | None
    state: str
    health: str | None

    def __str__(self) -> str:
        return (
            f"PowerSupplyReading("
            f"id={self.id}, "
            f"output={self.output_watts}W, "
            f"capacity={self.capacity_watts}W, "
            f"input={self.input_voltage}V, "
            f"state={self.state}, "
            f"health={self.health or 'unknown'}"
            f")"
        )


@dataclass(frozen=True, slots=True)
class PowerData:
    consumed_watts: int | None
    capacity_watts: int | None
    limit_watts: int | None
    power_supplies: list[PowerSupplyReading]

    def get_power_supplies(self, include_disabled: bool = False) -> list[PowerSupplyReading]:
        """Get the of each individual power supply readings.

        Args:
            include_disabled (bool, optional): Specifies wether to also get the disabled power supplies. Defaults to False.

        Returns:
            list[FanReading]: List with the individual power supply readings.
        """

        if include_disabled:
            return self.power_supplies.copy()

        return [supply for supply in self.power_supplies if supply.state == "Enabled"]

    def __str__(self) -> str:
        supplies = "\n".join(f"    {supply}" for supply in self.power_supplies)

        return (
            "PowerData[\n"
            f"  consumed={self.consumed_watts}W\n"
            f"  capacity={self.capacity_watts}W\n"
            f"  limit={self.limit_watts}W\n"
            "  PowerSupplies[\n"
            f"{supplies}\n"
            "  ]\n"
            "]"
        )


class ClientRESTError(Exception):
    pass


class ClientREST:
    CHASSIS_TERMAL_ENDPOINT = "/redfish/v1/Chassis/1/Thermal/"
    CHASSIS_POWER_ENDPOINT = "/redfish/v1/Chassis/1/Power/"

    def __init__(self):
        self._host = ILO_HOST
        self._username = ILO_ADMIN_USER
        self._password = ILO_ADMIN_PASSWORD

        self._client = httpx.AsyncClient(
            base_url=f"https://{self._host}",
            auth=httpx.BasicAuth(
                username=self._username,
                password=self._password,
            ),
            headers={
                "Accept": "application/json",
            },
            limits=httpx.Limits(
                max_connections=1,
                max_keepalive_connections=0,
            ),
            verify=False,
            trust_env=False,
            timeout=httpx.Timeout(
                connect=10.0,
                read=60.0,  # 60 because in tests the iLO module took up to 30 seconds to respond
                write=10.0,
                pool=10.0,
            ),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def request(self, method: str, endpoint: str) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                endpoint,
            )
            response.raise_for_status()

            data = response.json()

            if not isinstance(data, dict):
                raise ClientRESTError(f"Unexpected response from endpoint: {endpoint}")

            return data

        except httpx.HTTPError as error:
            logger.error(
                "iLO REST request failed: %s %s",
                method,
                endpoint,
            )
            raise ClientRESTError(f"iLO REST request failed: {method} {endpoint}") from error

        except ValueError as error:
            raise ClientRESTError(f"Invalid JSON returned by endpoint: {endpoint}") from error

    async def get_thermal_data(self) -> ThermalData:
        """Retrieves iLO chassis thermal data readings.

        Raises:
            ClientRESTError: Raised if an error occurred during the HTTP request to iLO.
        """

        data = await self.request(
            "GET",
            self.CHASSIS_TERMAL_ENDPOINT,
        )

        fans: list[FanReading] = []

        for raw_fan in data.get("Fans", []):
            if not isinstance(raw_fan, dict):
                continue

            name = raw_fan.get("FanName")

            if not isinstance(name, str):
                continue

            try:
                # Redfish Fan 1 corresponds to application fan ID 0.
                fan_id = int(name.rsplit(" ", 1)[1]) - 1
            except (ValueError, IndexError):
                logger.warning("Unable to determine fan ID from name: %s", name)
                continue

            status = raw_fan.get("Status", {})

            fans.append(
                FanReading(
                    id=fan_id,
                    name=name,
                    speed_percentage=raw_fan.get("CurrentReading"),
                    state=status.get("State", "Unknown"),
                    health=status.get("Health"),
                )
            )

        temperatures: list[TemperatureReading] = []

        for raw_temp in data.get("Temperatures", []):
            if not isinstance(raw_temp, dict):
                continue

            sensor_id = raw_temp.get("Number")
            name = raw_temp.get("Name")

            if type(sensor_id) is not int or not isinstance(name, str):
                continue

            status = raw_temp.get("Status", {})

            temperatures.append(
                TemperatureReading(
                    id=sensor_id,
                    name=name,
                    temperature_celsius=raw_temp.get("ReadingCelsius"),
                    physical_context=raw_temp.get("PhysicalContext"),
                    state=status.get("State", "Unknown"),
                    health=status.get("Health"),
                    critical_threshold_celsius=raw_temp.get("UpperThresholdCritical"),
                    fatal_threshold_celsius=raw_temp.get("UpperThresholdFatal"),
                )
            )

        return ThermalData(
            fans=fans,
            temperatures=temperatures,
        )

    async def get_power_data(self) -> PowerData:
        """Retrieve the current iLO chassis power data."""

        data = await self.request(
            "GET",
            self.CHASSIS_POWER_ENDPOINT,
        )

        raw_limit = data.get("PowerLimit", {})

        if not isinstance(raw_limit, dict):
            raw_limit = {}

        power_supplies: list[PowerSupplyReading] = []

        for index, raw_supply in enumerate(
            data.get("PowerSupplies", []),
            start=1,
        ):
            if not isinstance(raw_supply, dict):
                continue

            status = raw_supply.get("Status", {})

            if not isinstance(status, dict):
                status = {}

            hp_data = raw_supply.get("Oem", {}).get("Hp", {})

            power_supplies.append(
                PowerSupplyReading(
                    id=hp_data.get("BayNumber", index),
                    output_watts=raw_supply.get("LastPowerOutputWatts"),
                    capacity_watts=raw_supply.get("PowerCapacityWatts"),
                    input_voltage=raw_supply.get("LineInputVoltage"),
                    state=status.get("State", "Unknown"),
                    health=status.get("Health"),
                )
            )

        return PowerData(
            consumed_watts=data.get("PowerConsumedWatts"),
            capacity_watts=data.get("PowerCapacityWatts"),
            limit_watts=raw_limit.get("LimitInWatts"),
            power_supplies=power_supplies,
        )
