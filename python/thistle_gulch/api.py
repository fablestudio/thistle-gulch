import typing
from datetime import datetime

from . import logger

if typing.TYPE_CHECKING:
    from .runtime import Runtime


class API:

    def __init__(self, runtime: "Runtime"):
        self.runtime = runtime

    async def resume(self) -> None:
        """
        Start or resume the simulation using the last known simulation speed
        """
        logger.debug("Resuming simulation")
        await self.runtime.send_message(
            "simulation-command",
            {
                "command": "resume",
            },
        )

    async def pause(self) -> None:
        """
        Pause the simulation
        """
        logger.debug("Pausing simulation")
        await self.runtime.send_message(
            "simulation-command",
            {
                "command": "pause",
            },
        )

    async def set_speed(self, speed: str) -> None:
        """
        Change the speed of the simulation

        :param speed: A string representing one of the pre-defined speed constants:
                'Realtime'
                'OneMinutePerSecond'
                'FiveMinutesPerSecond'
                'TenMinutesPerSecond'
                'TwentyMinutesPerSecond'
        """
        logger.debug(f"Setting simulation speed to {speed}")
        await self.runtime.send_message(
            "simulation-command",
            {
                "command": "set-speed",
                "speed": speed,
            },
        )

    async def set_start_date(self, date: datetime) -> None:
        """
        Set the simulation start date. Only works if the simulation has not been started yet.

        :param date: A datetime object representing the start date of the simulation
        """
        logger.debug(f"Setting simulation start date to {date.isoformat()}")
        await self.runtime.send_message(
            "simulation-command",
            {
                "command": "set-start-date",
                "iso_date": date,
            },
        )
