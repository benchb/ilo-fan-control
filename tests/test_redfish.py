import asyncio
import os

import pytest


REQUIRED_ENV_VARIABLES = (
    "ILO_HOST",
    "ILO_ADMIN_USER",
    "ILO_ADMIN_PASSWORD",
)

missing_env_variables = [variable for variable in REQUIRED_ENV_VARIABLES if not os.getenv(variable)]

if missing_env_variables:
    pytest.skip(
        "Missing required iLO environment variables: " + ", ".join(missing_env_variables),
        allow_module_level=True,
    )


from ilo_fan_control.ilo.redfish import ClientREST, PowerData, ThermalData


def test_rest_data_retrieval() -> None:
    async def run_test() -> None:
        client = ClientREST()

        try:
            thermal_data = await client.get_thermal_data()

            assert isinstance(thermal_data, ThermalData)
            assert thermal_data.fans
            assert thermal_data.temperatures

            power_data = await client.get_power_data()

            assert isinstance(power_data, PowerData)
            assert power_data.consumed_watts is not None
            assert power_data.capacity_watts is not None
            assert power_data.power_supplies

        finally:
            await client.close()

        assert client._client.is_closed

    asyncio.run(run_test())
