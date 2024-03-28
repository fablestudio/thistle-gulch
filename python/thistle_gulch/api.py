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
        self.runtime.start_date = date

    async def enable_agent(self, persona_id: str, enabled: bool) -> None:
        """
        Enable or disable the LLM agent for the given persona_id.
        Enabled agents generate their actions using the python Bridge.
        Disabled agents generate their actions in the simulation Runtime using a simple scoring system.

        :param persona_id: persona to modify
        :param enabled: Flag to Enable or disable the agent
        """
        logger.debug(f"{('Enabling' if enabled else 'Disabling')} agent: {persona_id}")
        await self.runtime.send_message(
            "simulation-command",
            {
                "command": "enable-agent",
                "persona_id": persona_id,
                "enabled": enabled,
            },
        )

    async def update_character_property(
        self, persona_id: str, property_name: str, value: str
    ) -> None:
        """
        Update a property value for the given persona

        :param persona_id: Persona to modify
        :param property_name: Name of the property to modify
        :param value: Value to assign to the property
        """
        logger.debug(f"Updating {persona_id} {property_name} to '{value}'")
        await self.runtime.send_message(
            "simulation-command",
            {
                "command": "update-character-property",
                "persona_id": persona_id,
                "property": property_name,
                "value": value,
            },
        )
