import typing
from datetime import datetime

from . import logger, converter
from .data_models import PersonaContextObject

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
            "character-command",
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
            "character-command",
            {
                "command": "update-character-property",
                "persona_id": persona_id,
                "property": property_name,
                "value": value,
            },
        )

    async def get_character_context(self, persona_id: str) -> PersonaContextObject:
        """
        Request all contextual information about a specific character

        :param persona_id: Persona to modify
        """
        logger.debug(f"Requesting context for {persona_id}")
        response = await self.runtime.send_message(
            "character-command",
            {"command": "request-character-context", "persona_id": persona_id},
        )
        context = converter.structure(
            response.data.get("context_obj"), PersonaContextObject
        )
        return context

    async def override_character_action(self, persona_id: str, action: dict) -> None:
        """
        Interrupt the character's current action with a new one

        :param persona_id: Persona to modify
        :param action: The new action to execute
        """
        logger.debug(f"Overriding action for {persona_id} with {action}")
        await self.runtime.send_message(
            "character-command",
            {
                "command": "override-character-action",
                "persona_id": persona_id,
                "action": action,
            },
        )

    async def focus_character(self, persona_id: str) -> None:
        """
        Focusing a character shows the character UI and navigation path, and allows the player to take actions on their behalf

        :param persona_id: Persona to focus. If none provided, the currently focused character will be removed from focus.
        """
        logger.debug(f"Focus {persona_id}")
        await self.runtime.send_message(
            "character-command",
            {
                "command": "focus_character",
                "persona_id": persona_id,
            },
        )

    async def follow_character(self, persona_id: str, zoom: float) -> None:
        """
        Follow a specific character with the camera

        :param persona_id: Persona to follow. If none provided, stop following the current character if any.
        :param zoom: The camera zoom amount between 0.0 (furthest) and 1.0 (closest)
        """
        logger.debug(f"Following {persona_id} with the camera")
        await self.runtime.send_message(
            "camera-command",
            {
                "command": "follow_character",
                "persona_id": persona_id,
                "zoom": zoom,
            },
        )
