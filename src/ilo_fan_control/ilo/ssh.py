import logging
import asyncio
import asyncssh
from ilo_fan_control.env import ILO_HOST, ILO_ADMIN_USER, ILO_ADMIN_PASSWORD

logger = logging.getLogger(__name__)

# SSH client constants
MAX_ATTEMPTS = 5
RETRY_DELAY = 2.0
_CONNECTION_ERRORS = (
    asyncssh.Error,
    OSError,
    EOFError,
    TimeoutError,
    asyncio.IncompleteReadError,
)


class ClientSSHError(Exception):
    pass


class ClientSSH:
    def __init__(self):
        self._host = ILO_HOST
        self._username = ILO_ADMIN_USER
        self._password = ILO_ADMIN_PASSWORD

        self._connection: asyncssh.SSHClientConnection | None = None
        self._process: asyncssh.SSHClientProcess | None = None
        self._lock = asyncio.Lock()

    def is_connected(self) -> bool:
        """Checks wether the SSH client is connected.

        Returns:
            bool: True if connected; False otherwise.
        """
        return (
            self._connection is not None
            and not self._connection.is_closed()
            and self._process is not None
            and not self._process.is_closing()
        )

    async def close(self) -> None:
        """Closes the current connection, if there is any."""

        if self._connection is None:
            return

        self._connection.close()
        await self._connection.wait_closed()

        self._connection = None
        self._process = None

    async def connect(self) -> None:
        """Opens an SSH connection with the iLO server. Forces a new one, if there is one already."""

        await self.close()

        self._connection = await asyncssh.connect(
            self._host,
            username=self._username,
            password=self._password,
            known_hosts=None,  # skips host verification
            kex_algs=["diffie-hellman-group1-sha1"],  # required for older iLOs
            server_host_key_algs=["ssh-rsa"],  # also for compatibility
        )

        self._process = await self._connection.create_process(
            term_type="vt100",
            term_size=(80, 24),
            request_pty=True,
        )

        # Consume the login banner and initial prompt.
        await asyncio.wait_for(
            self._process.stdout.readuntil(">"),
            timeout=10,
        )

    async def _run_command(self, command: str) -> str:
        assert self._process is not None

        self._process.stdin.write(f"{command}\r")
        await self._process.stdin.drain()

        return await asyncio.wait_for(
            self._process.stdout.readuntil(">"),
            timeout=10,
        )

    async def run(self, command: str) -> str:
        """Executes a command through the iLO SSH.

        Args:
            command (str): The command to execute on the iLO server.

        Raises:
            ClientSSHError: An error is raised if command fails after a
                            configured amount of times

        Returns:
            str: The output of the command if successful.
        """

        async with self._lock:
            last_error: Exception | None = None

            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    if not self.is_connected():
                        await self.connect()

                    return await self._run_command(command)

                except _CONNECTION_ERRORS as error:
                    last_error = error
                    await self.close()

                    if attempt < MAX_ATTEMPTS:
                        logger.warning(
                            "SSH command failed (%d/%d). Retrying in %.1f seconds...",
                            attempt,
                            MAX_ATTEMPTS,
                            RETRY_DELAY,
                        )
                        await asyncio.sleep(RETRY_DELAY)

            logger.critical(
                "Failed to execute SSH command after %d attempts.",
                MAX_ATTEMPTS,
            )

            raise ClientSSHError(
                f"Failed to execute command after {MAX_ATTEMPTS} attempts: {command}"
            ) from last_error

    async def set_fan_speed(self, fan_id: int, percentage: int) -> None:
        """Changes the fan from PID to locked speed configuration.
        In this config, the fans will not respond to overheating.

        Args:
            fan_id (int): iLO integer ID of the Fan.
            percentage (int): A percentage value for the Fan speed (0-100)

        Raises:
            ValueError: Raised if the percentage value is not valid or outside of the range.
        """

        # Make sure it is a valid percentage integer
        if type(percentage) is not int or not 0 <= percentage <= 100:
            raise ValueError("Fan speed must be an integer between 0 and 100.")

        # Convert to PWM range 0-255
        pwm = round(percentage * 255 / 100)

        await self.run(f"fan p {fan_id} lock {pwm}")

    async def set_fan_auto(self, fan_id: int) -> None:
        """Chsnges the Fan from a locked configuration to the default iLO PID control.

        Args:
            fan_id (int): iLO integer ID of the Fan.
        """
        await self.run(f"fan p {fan_id} unlock")
