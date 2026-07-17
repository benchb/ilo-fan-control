import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ilo_fan_control.data.states import AppState, Profiles
from ilo_fan_control.models.fans import Fans

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Initialize state variables
    configured_fans = Fans()
    profiles = Profiles(configured_fans)
    app_state = AppState(
        configured_fans,
        profiles,
    )

    # Save state variables in FastAPI state
    app.state.fans = configured_fans
    app.state.profiles = profiles
    app.state.app_state = app_state

    # Log the initial state for debug
    logger.debug("%s", configured_fans)
    logger.debug("%s", profiles.all())
    logger.debug("%s", app_state)

    yield


app = FastAPI(
    title="iLO Fan Control",
    description="Web application for monitoring and controlling HPE iLO fan speeds.",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
