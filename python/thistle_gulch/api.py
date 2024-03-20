import typing

from . import logger

if typing.TYPE_CHECKING:
    from .runtime import Runtime


class API:

    def __init__(self, runtime: "Runtime"):
        self.runtime = runtime

    async def resume(self) -> None:
        """
        Start or resume the simulation using the last known simulation speed

        :param callback: An optional callback that is executed when the message response is received
        """
        logger.info("Resuming simulation")
        await self.runtime.send_message('simulation-command', {
            'command': 'resume',
        })

    async def pause(self) -> None:
        """
        Pause the simulation

        :param callback: An optional callback that is executed when the message response is received
        """
        logger.info("Pausing simulation")
        await self.runtime.send_message('simulation-command', {
            'command': 'pause',
        })

    async def set_speed(self, speed: str) -> None:
        """
        Change the speed of the simulation

        :param speed: A string representing one of the pre-defined speed constants:
                'Realtime'
                'OneMinutePerSecond'
                'FiveMinutesPerSecond'
                'TenMinutesPerSecond'
                'TwentyMinutesPerSecond'

        :param callback: An optional callback that is executed when the message response is received
        """
        logger.info(f"Setting simulation speed to {speed}")
        await self.runtime.send_message('simulation-command', {
            'command': 'set-speed',
            'speed': speed,
        })

    async def set_start_date(self, iso_date: str) -> None:
        """
        Set the simulation start date using an ISO 8601 string

        :param iso_date: Any parseable datetime string:
            '2000-01-01' - Midnight on January 1, 2000
            '2000-01-01T08:00:00.00' - 8am on January 1, 2000

        :param callback: An optional callback that is executed when the message response is received
        """
        logger.info(f"Setting simulation start date to {iso_date}")
        await self.runtime.send_message('simulation-command', {
            'command': 'set-start-date',
            'iso_date': iso_date,
        })
