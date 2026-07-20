import asyncio
import os

import pytest


REQUIRED_ENV_VARIABLES = (
    "ILO_HOST",
    "ILO_ADMIN_USER",
    "ILO_ADMIN_PASSWORD",
)

missing_env_variables = [
    variable
    for variable in REQUIRED_ENV_VARIABLES
    if not os.getenv(variable)
]

if missing_env_variables:
    pytest.skip(
        "Missing required iLO environment variables: "
        + ", ".join(missing_env_variables),
        allow_module_level=True,
    )


from ilo_fan_control.ilo.ssh import ClientSSH


FAN_ID = 0
TEST_SPEED_PERCENTAGE = 100


def test_ssh_fan_control() -> None:
    async def run_test() -> None:
        client = ClientSSH()

        try:
            await client.connect()
            assert client.is_connected()

            await client.set_fan_speed(
                FAN_ID,
                TEST_SPEED_PERCENTAGE,
            )

        finally:
            if client.is_connected():
                try:
                    await client.set_fan_auto(FAN_ID)
                finally:
                    await client.close()

        assert not client.is_connected()

    asyncio.run(run_test())