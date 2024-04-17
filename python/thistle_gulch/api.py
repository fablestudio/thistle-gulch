import typing
from typing import List
from datetime import datetime

from . import logger, converter
from .data_models import PersonaContextObject

if typing.TYPE_CHECKING:
    from .runtime import Runtime


class API:
    """
    See the wiki for more information: https://github.com/fablestudio/thistle-gulch/wiki/API
    """

    def __init__(self, runtime: "Runtime"):
        self.runtime = runtime

    async def resume(self) -> None:
        """
        Start or resume the simulation using the last known simulation speed. Resume can only be called if the simulation
        is currently paused or an error will be thrown. on_tick events are sent from the Runtime on every simulation
        tick once it has been resumed. This has the same effect as pressing the Play button in the Runtime Time Panel
        in the lower right corner of the UI.
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
        Pause the simulation. The simulation time clock will no longer be incremented, on_tick events will no longer be
        sent from the Runtime, and all characters will freeze in place. The Runtime remains interactive however - the
        camera can still be moved and objects can be inspected. Pausing can be useful for executing long-running tasks
        that need to completed before resuming the simulation. This has the same effect as pressing the Pause button in
        the Runtime Time Panel in the lower right corner of the UI.
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
        Change the speed of the simulation. The default play speed of the simulation is one minute of sim time per
        second of real time, but sometimes this is too slow if we're waiting to see the effect of an action that takes
        hours or days of simulation time to complete. A set of predefined speed constants is provided to allow the
        simulation to run at up to 20 minutes of sim time per second of real time.

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
        Set the simulation start date and time. This is the date at which the "Day 1" of simulation time is calculated
        in the Time Panel. By default, the simulation starts at 8am so this can be useful for changing the time of day
        to something else, which in turn affects the environment lighting in the Runtime. Must be set in the on_resume
        callback otherwise an error will be thrown - changing the date or time after the simulation has started is not
        currently supported.

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
        Enable or disable the Bridge agent for a specific character. Enabled agents generate their actions using the
        python Bridge by sending requests to generate action options. Disabled agents generate their actions in the
        simulation Runtime using a simple scoring system similar to the one used by The Sims. The agent state does not
        affect conversation generation - all characters use the Bridge for this purpose.

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
        Set a character property to a new value. Characters in Thistle Gulch come with a set of pre-defined properties
        such as energy, description, and backstory which ultimately define the behavior of the character in the
        simulation via the generation of actions and conversations. For instance, changing a character's backstory
        alters their motivations and can lead them to make very different decisions when interacting with other characters.

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
        Request all contextual information about a specific character and other relevant world states. This includes
        things like available interactions, memories, conversations, current action, and other details. This information
        can be used in many different ways: construct actions using skills, use the current time to trigger an event,
        observe what other characters are doing or conversing about, finding available locations to travel to, etc.

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
        Interrupt the character's current action with the one provided. An action is constructed using one of the
        available skills and sent to the Runtime, which causes the character to immediately stop their current action
        and begin the new one. This can be useful for orchestrating a series of events over time, or in response to
        another action that was executed in the simulation. Keep in mind that while the action is guaranteed to start
        executing, other events in the simulation may still interrupt it for various reasons (e.g. energy goes to zero,
        character is arrested, etc.)

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
        Focusing a character shows the character UI and navigation path, and allows the player to take actions on their
        behalf. A focused character's name label is highlighted, and their chat bubble (and those of any conversation
        partners) will render on top of everything else. Calling focus_character with a null character id will clear the
        focus state. Focusing does not cause the camera to follow the character - use the follow_character command if
        this is desired.

        :param persona_id: Persona to focus. If none provided, the currently focused character will be removed from focus.
        """
        logger.debug(f"Focus {persona_id}")
        await self.runtime.send_message(
            "character-command",
            {
                "command": "focus-character",
                "persona_id": persona_id,
            },
        )

    async def follow_character(self, persona_id: str, zoom: float) -> None:
        """
        Follow a specific character with the camera. When triggered, the camera pivot instantly moves to the given
        character and follows them as they navigate around the world. Calling follow_character with a null character id
        will cause the camera to stop following. A followed character's name label and chat bubble (and those of any
        conversation partners) will render on top of everything else.

        :param persona_id: Persona to follow. If none provided, stop following the current character if any.
        :param zoom: The camera zoom amount between 0.0 (furthest) and 1.0 (closest)
        """
        logger.debug(f"Following {persona_id} with the camera")
        await self.runtime.send_message(
            "camera-command",
            {
                "command": "follow-character",
                "persona_id": persona_id,
                "zoom": zoom,
            },
        )

    async def place_camera(
        self,
        position_x: float,
        position_y: float,
        position_z: float,
        rotation_x: float,
        rotation_y: float,
        rotation_z: float,
        field_of_view: float,
    ) -> None:
        """
        Place the camera with a specific position, rotation and field of view. This temporarily switches to the "God"
        camera mode - Press ESC or click anywhere in the screen to restore the default camera mode. Useful for
        programmatically moving the camera for cinematic purposes.

        :param position_x: X position in meters
        :param position_y: Y position in meters
        :param position_z: Z position in meters
        :param rotation_x: X rotation in degrees - euler angle between -360 and +360
        :param rotation_y: Y rotation in degrees - euler angle between -360 and +360
        :param rotation_z: Z rotation in degrees - euler angle between -360 and +360
        :param field_of_view: Field of view in degrees - angle between 5 and 120
        """
        logger.debug(
            f"Placing camera at \n\tposition: {position_x, position_y, position_z}\n\trotation: {rotation_x, rotation_y, rotation_z}\n\tfov: {field_of_view}"
        )
        await self.runtime.send_message(
            "camera-command",
            {
                "command": "place-camera",
                "position_x": position_x,
                "position_y": position_y,
                "position_z": position_z,
                "rotation_x": rotation_x,
                "rotation_y": rotation_y,
                "rotation_z": rotation_z,
                "field_of_view": field_of_view,
            },
        )

    async def modal(
        self, title: str, message: str, buttons: List[str], pause: bool = True
    ) -> None:
        """
        Display a modal dialog with a title and message. This is a blocking operation - the simulation will not continue
        until the user dismisses the dialog. Modals are useful for getting user input or displaying important information
        that requires immediate attention.

        :param title: Title of the modal dialog
        :param message: Message to display in the dialog
        """
        logger.debug(
            f"Displaying modal dialog with title: {title} and message: {message}"
        )
        await self.runtime.send_message(
            "simulation-command",
            {
                "command": "modal",
                "title": title,
                "message": message,
                "buttons": buttons,
                "pause": pause,
            },
        )
