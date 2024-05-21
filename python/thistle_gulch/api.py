import asyncio
import uuid
from enum import Enum
from typing import List, Optional, TYPE_CHECKING, Dict, Any
from datetime import datetime
from asyncio import Future

import cattrs
from fable_saga.actions import Action

from . import logger, converter
from .data_models import PersonaContextObject, WorldContextObject, Memory, Vector3, TokenUsage

if TYPE_CHECKING:
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

    class SimulationSpeed(Enum):
        REALTIME = "Realtime"
        ONE_MINUTE_PER_SECOND = "OneMinutePerSecond"
        FIVE_MINUTES_PER_SECOND = "FiveMinutesPerSecond"
        TEN_MINUTES_PER_SECOND = "TenMinutesPerSecond"
        TWENTY_MINUTES_PER_SECOND = "TwentyMinutesPerSecond"

    async def set_speed(self, speed: SimulationSpeed) -> None:
        """
        Change the speed of the simulation. The default play speed of the simulation is one minute of sim time per
        second of real time, but sometimes this is too slow if we're waiting to see the effect of an action that takes
        hours or days of simulation time to complete. A set of predefined speed constants is provided to allow the
        simulation to run at up to 20 minutes of sim time per second of real time.

        :param speed: The new simulation speed to activate
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

    async def enable_agent(
        self,
        persona_guid: str,
        actions: Optional[bool] = None,
        conversations: Optional[bool] = None,
    ) -> None:
        """
        Enable or disable the Bridge for action and/or conversation generation. Generates actions using the
        python Bridge by sending requests to generate action options. When bridge actions are disabled, actions are
        generated in the simulation Runtime using a simple scoring system similar to the one used by The Sims.
        Conversations are only generated via the bridge - if disabled

        :param persona_guid: persona to modify
        :param actions: Enable or disable the agent's action generation
        :param conversations: Enable or disable the agent's conversation generation
        """

        if actions is None and conversations is None:
            logger.error(
                f"Failed to enable agent for '{persona_guid}' - at least one of the 'actions' or 'conversations' arguments must be set"
            )
            return

        data: Dict[str, Any] = {"command": "enable-agent", "persona_guid": persona_guid}
        if actions is not None:
            data["actions"] = actions
            logger.debug(
                f"{('Enabling' if actions else 'Disabling')} actions: {persona_guid}"
            )
        if conversations is not None:
            data["conversations"] = conversations
            logger.debug(
                f"{('Enabling' if conversations else 'Disabling')} conversations: {persona_guid}"
            )

        await self.runtime.send_message(
            "character-command",
            data,
        )

    async def character_memory_add(
        self,
        persona_guid: str,
        timestamp: str,
        summary: str,
        entity_ids: Optional[List[str]] = None,
        position: Optional[Vector3] = None,
        importance_weight: float = 0.5,
    ) -> Memory:
        """
        Add a new memory to a character. A subset of these memories are included automatically in the conversation and
        action generation prompts based on their importance_weight. Memories can be accessed from the WorldContextObject
        via api.get_world_context().

        :param persona_guid: Persona to add the memory to.
        :param timestamp: A datetime string representation of when the memory occurred.
        :param summary: A text description of the memory.
        :param entity_ids: The ids of the personas or objects involved in the memory
        :param position: The XYZ coordinates where the memory occurred.
        :param importance_weight: The importance of this memory to the character. Any weight greater than 1 has priority
            inclusion in the conversation and action generation prompts.
        """

        if entity_ids is None:
            entity_ids = [persona_guid]
        if importance_weight is None:
            importance_weight = 0.5

        memory = Memory(
            guid=str(uuid.uuid4()),
            timestamp=timestamp,
            summary=summary,
            context_id=persona_guid,
            entity_ids=entity_ids,
            position=position,
            importance_weight=importance_weight,  # Any weight greater than 1 has priority inclusion in the conversation and action generation prompts
        )

        logger.debug(f"Adding memory to {persona_guid}: {memory}")
        await self.runtime.send_message(
            "character-command",
            {
                "command": "character-memory-add",
                "persona_guid": persona_guid,
                "memory": memory,
            },
        )

        return memory

    async def character_memory_remove(self, persona_guid: str, memory_id: str) -> None:
        """
        Remove a specific memory from a character by id. Memories can be accessed from the WorldContextObject
        via api.get_world_context().

        :param persona_guid: Persona to modify
        :param memory_id: The guid of the memory to remove
        """
        logger.debug(f"Removing memory from {persona_guid}: {memory_id}")
        await self.runtime.send_message(
            "character-command",
            {
                "command": "character-memory-remove",
                "persona_guid": persona_guid,
                "memory_id": memory_id,
            },
        )

    async def character_memory_clear(self, persona_guid: str) -> None:
        """
        Clear all memories for a specific character. Useful for clearing pre-defined character memories in preparation
        for replacing them with new ones.

        :param persona_guid: Persona to modify
        """
        logger.debug(f"Clearing all memories for {persona_guid}")
        await self.runtime.send_message(
            "character-command",
            {"command": "character-memory-clear", "persona_guid": persona_guid},
        )

    async def update_character_properties(
        self, persona_guid: str, property_values: Dict[str, Any]
    ) -> None:
        """
        Set one or more character properties to a new value. Characters in Thistle Gulch come with a set of pre-defined
        properties such as energy, description, and backstory which ultimately define the behavior of the character in
        the simulation via the generation of actions and conversations. For instance, changing a character's backstory
        alters their motivations and can lead them to make very different decisions when interacting with other
        characters.

        :param persona_guid: Persona to modify
        :param property_values: Map from property names to their new values
        """

        logger.debug(f"Updating {persona_guid} properties to {property_values}")
        await self.runtime.send_message(
            "character-command",
            {
                "command": "update-character-properties",
                "persona_guid": persona_guid,
                "properties": list(property_values.keys()),
                "values": list(property_values.values()),
            },
        )

    async def get_world_context(self) -> WorldContextObject:
        """
        Request all contextual information from the simulation world. This includes things like available interactions,
        memories, conversations, skills, etc. This information can be used in many different ways: construct actions
        using skills, use the current time to trigger an event, observe what other characters are doing or conversing
        about, finding available locations to travel to, etc.
        """
        logger.debug(f"Requesting world context")
        response = await self.runtime.send_message(
            "simulation-command",
            {"command": "request-world-context"},
        )
        context = converter.structure(
            response.data.get("context_obj"), WorldContextObject
        )
        return context

    async def get_character_context(self, persona_guid: str) -> PersonaContextObject:
        """
        Request contextual information about a specific character. This is useful for understanding the current state of
        a character when generating actions or conversations for instance. The character context also contains the world
        context for convenience.

        :param persona_guid: Persona to query
        """
        logger.debug(f"Requesting context for {persona_guid}")
        response = await self.runtime.send_message(
            "character-command",
            {"command": "request-character-context", "persona_guid": persona_guid},
        )
        context = converter.structure(
            response.data.get("context_obj"), PersonaContextObject
        )
        return context

    async def override_character_action(
        self,
        persona_guid: str,
        action: Optional[Action],
        future: Optional[Future] = None,
        wait: bool = False,
    ) -> None:
        """
        Interrupt the character's current action with the one provided. An action is constructed using one of the
        available skills and sent to the Runtime, which causes the character to immediately stop their current action
        and begin the new one. This can be useful for orchestrating a series of events over time, or in response to
        another action that was executed in the simulation. Keep in mind that while the action is guaranteed to start
        executing, other events in the simulation may still interrupt it for various reasons (e.g. energy goes to zero,
        character is arrested, etc.)

        :param persona_guid: Persona to modify
        :param action: [Optional] The new action to execute. If None, interrupt the current action instead.
        :param future: [Optional] A future that can be awaited until the action is completed. If not provided,
            the on_action_completed callback will be called when the action is completed instead.
        :param wait: [Optional] Flag to wait for a new action to be manually triggered after completing. If False,
            the next action will automatically be generated by the character's agent. If true, the on_action_completed
            event will not be triggered either.
        """
        action_data = cattrs.unstructure(action) if action is not None else None

        logger.debug(f"Overriding action for {persona_guid} with {action}")
        await self.runtime.send_message(
            "character-command",
            {
                "command": "override-character-action",
                "persona_guid": persona_guid,
                "action": action_data,
                "wait_after": wait,
            },
            future,
        )

    class FocusPanelTab(Enum):
        NONE = ""
        CALENDAR = "Calendar"
        CHARACTER_DETAILS = "CharacterDetails"
        HISTORY = "History"

    async def focus_character(
        self, persona_guid: str, open_tab: FocusPanelTab = FocusPanelTab.NONE
    ) -> None:
        """
        Focusing a character shows the character UI and navigation path, and allows the player to take actions on their
        behalf. A focused character's name label is highlighted, and their chat bubble (and those of any conversation
        partners) will render on top of everything else. Calling focus_character with a null character id will clear the
        focus state. Focusing does not cause the camera to follow the character - use the follow_character command if
        this is desired.

        :param persona_guid: Persona to focus. If none provided, the currently focused character will be removed from focus.
        :param open_tab: Optional focus panel tab to open. Simulates clicking one of the tab icons in the focus panel.
        """
        logger.debug(f"Focusing {persona_guid}")
        await self.runtime.send_message(
            "character-command",
            {
                "command": "focus-character",
                "persona_guid": persona_guid,
                "open_tab": open_tab,
            },
        )

    async def follow_character(self, persona_guid: str, zoom: float) -> None:
        """
        Follow a specific character with the camera. When triggered, the camera pivot instantly moves to the given
        character and follows them as they navigate around the world. Calling follow_character with a null character id
        will cause the camera to stop following. A followed character's name label and chat bubble (and those of any
        conversation partners) will render on top of everything else.

        :param persona_guid: Persona to follow. If none provided, stop following the current character if any.
        :param zoom: The camera zoom amount between 0.0 (furthest) and 1.0 (closest)
        """
        logger.debug(f"Following {persona_guid} with the camera")
        await self.runtime.send_message(
            "camera-command",
            {
                "command": "follow-character",
                "persona_guid": persona_guid,
                "zoom": zoom,
            },
        )

    async def place_camera(
        self,
        position: Vector3,
        rotation: Vector3,
        field_of_view: float,
    ) -> None:
        """
        Place the camera with a specific position, rotation and field of view. This temporarily switches to the "God"
        camera mode - Press the camera icon to restore the default camera mode. Useful for
        programmatically moving the camera for cinematic purposes.

        :param position: Position XYZ in meters
        :param rotation: Rotation XYZ in degrees - euler angle between -360 and +360
        :param field_of_view: Field of view in degrees - angle between 5 and 120
        """
        logger.debug(
            f"Placing camera at \n\tposition: {position}\n\trotation: {rotation}\n\tfov: {field_of_view}"
        )
        await self.runtime.send_message(
            "camera-command",
            {
                "command": "place-camera",
                "position": position,
                "rotation": rotation,
                "field_of_view": field_of_view,
            },
        )

    async def place_character(
        self,
        persona_guid: str,
        position: Vector3,
        rotation: Vector3,
    ) -> None:
        """
        Place a character with a specific position and rotation. TODO

        :param persona_guid: The id of the character to place
        :param position: Position XYZ in meters
        :param rotation: Rotation XYZ in degrees - euler angle between -360 and +360
        """
        logger.debug(
            f"Placing character at \n\tposition: {position}\n\trotation: {rotation}"
        )
        await self.runtime.send_message(
            "character-command",
            {
                "command": "place-character",
                "persona_guid": persona_guid,
                "position": position,
                "rotation": rotation,
            },
        )

    async def modal(
        self,
        title: str,
        message: str,
        buttons: Optional[List[str]] = None,
        pause: bool = True,
        future: Optional[Future] = None,
    ) -> None:
        """
        Display a modal dialog with a title and message and button options. Modals are useful for getting user input
        or displaying important information that requires immediate attention.

        :param title: Title of the modal dialog
        :param message: Message to display in the dialog
        :param buttons: List of button labels to display in the dialog
        :param pause: Flag to pause the simulation while the dialog is displayed or not. Set to False if
            using a modal during the on_ready event.
        :param future: [Optional] A future that can be awaited until the response is received. If not provided, the
            on_event callback will be called when the choice is made instead.
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
            future,
        )

    async def add_cost(self, model_name: str, usage: TokenUsage) -> None:
        """
        Notify the Runtime of a cost to the simulation based on token usage.

        This is generally handled during SAGA (actions and conversation generation) with openai automatically as
        information in the llm_info object of the response, but this can be used to manually add costs to the simulation
        if needed. Example when using an LLM outside of SAGA requests.

        Args:
            model_name: The name of the model that incurred the cost. (e.g. "gpt-3.5-turbo")
            usage: The token usage object containing the number of tokens used for completion and prompt and their costs.
        """
        logger.debug(f"Adding cost for model: {model_name}")
        await self.runtime.send_message(
            "simulation-command",
            {
                "command": "add-cost",
                "modal_name": model_name,
                "token_usage": usage,
            },
        )
