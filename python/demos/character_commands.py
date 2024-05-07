import asyncio
from datetime import datetime, timedelta

from thistle_gulch.bridge import RuntimeBridge
from thistle_gulch.data_models import (
    WorldContextObject,
    Vector3,
)
from thistle_gulch.skills import (
    ConverseWithSkill,
    InteractSkill,
    WaitSkill,
    TakeToSkill,
)
from . import (
    Demo,
    choose_from_list,
    formatted_input_async,
    disable_all_agents,
    formatted_input,
)

CATEGORY = "Character Commands"


# noinspection PyAttributeOutsideInit
class EnableAgentDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Enable Agent",
            summary="Enables action and conversation generation for the chosen character",
            category=CATEGORY,
            function=self.enable_agent_demo,
        )

    def enable_agent_demo(self, bridge: RuntimeBridge):
        """
        On simulation start, the chosen character's bridge agent is enabled or disabled. Enabled agents use the
        Bridge to generate their actions and conversations and will contribute to the overall cost of running the
        simulation [when using a paid LLM service like OpenAI.] Disabled agents choose their actions directly in the
        simulation Runtime using a simpler utility AI based on scored affordances (like the SIMs) instead of sending
        requests to the Bridge. There is no fallback if conversation generation is disabled.

        API calls:
            enable_agent()
            follow_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        async def on_ready(_, world_context: WorldContextObject) -> bool:

            await disable_all_agents(bridge, world_context)

            personas = dict(
                [
                    (persona.persona_guid, persona.summary)
                    for persona in world_context.personas
                ]
            )
            persona_guid = await choose_from_list(
                "Enter persona id to enable their agent", personas
            )

            print(f"Enabling agent: {persona_guid}")
            await bridge.runtime.api.enable_agent(persona_guid, True, True)

            print(f"Following {persona_guid} with the camera")
            await bridge.runtime.api.follow_character(persona_guid, 0.8)

            return True

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class UpdateCharacterPropertyDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Update Character Property",
            summary="Change one of Jack Kane's property values to a new value",
            category=CATEGORY,
            function=self.update_character_property,
        )

    def update_character_property(self, bridge: RuntimeBridge):
        """
        On simulation start, Jack Kane's property is updated to the value provided. His agent may optionally be enabled
        which is useful for seeing the effect of the new value during action and conversation generation. The character
        is also focused for ease of access to the character details UI to inspect the changes. The currently available
        properties are energy, summary, description, and backstory, but this list will continue to expand in the future.

        API calls:
            update_character_properties()
            enable_agent()
            follow_character()
            focus_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        persona_guid = "jack_kane"

        def validate_property_name(name: str) -> str:
            if name not in [
                "energy",
                "summary",
                "description",
                "backstory",
            ]:
                raise ValueError(f"Invalid property name: {name}")
            return name

        property_name = formatted_input(
            "Enter property name (energy, summary, description, backstory)",
            validator=validate_property_name,
        )

        property_value = formatted_input(f"Enter new value for {property_name}")

        async def on_ready(_, world_context: WorldContextObject) -> bool:

            await disable_all_agents(bridge, world_context)

            property_values = {
                property_name: property_value
            }
            print(f"Updating {persona_guid} properties to {property_values}")
            await bridge.runtime.api.update_character_properties(
                persona_guid, property_values
            )

            print(f"Focusing {persona_guid}")
            await bridge.runtime.api.focus_character(
                persona_guid, bridge.runtime.api.FocusPanelTab.CHARACTER_DETAILS
            )

            print(f"Following {persona_guid} with the camera")
            await bridge.runtime.api.follow_character(persona_guid, 0.8)

            # Ask player to enable the agent
            future = asyncio.get_event_loop().create_future()
            await bridge.runtime.api.modal(
                "Character Property Updated",
                f"The '{property_name}' property has been updated. The new value can be found in the character details UI to the left.\n\n"
                f"Do you want to enable {persona_guid}'s SAGA agent to test the results of your change?",
                ["Yes", "No"],
                True,
                future=future,
            )
            modal_response = await future
            choice_idx = modal_response["choice"]
            if choice_idx == 0:
                print(f"Enabling {persona_guid}'s agent")
                await bridge.runtime.api.enable_agent(persona_guid, True, True)

            return True

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class ChangeCharacterMemoriesDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Change Character Memories",
            summary="Clear Wyatt Cooper's memories and replace them with new ones",
            category=CATEGORY,
            function=self.change_character_memories,
        )

    def change_character_memories(self, bridge: RuntimeBridge):
        """
        All of Wyatt Cooper's memories are erased and replaced with new ones, then his agent is enabled to use these new
        memories. The world context is obtained to demonstrate how to remove a single memory by id, all his memories are
        cleared, and then new memories are added to replace the ones he had initially.

        API calls:
            get_world_context()
            character_memory_remove()
            character_memory_clear()
            character_memory_add()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        persona_guid = "wyatt_cooper"

        async def on_ready(_, world_context: WorldContextObject) -> bool:

            await disable_all_agents(bridge, world_context)

            # Find the first existing memory and remove it
            # This is only for demostration purposes, see below where we use api.character_memory_clear to remove all memories
            old_memories = next(
                m for m in world_context.memories if m.persona_guid == persona_guid
            )
            first_memory = (
                old_memories.memories[0]
                if old_memories and len(old_memories.memories) > 0
                else None
            )
            if first_memory is not None:
                print(f"Removing memory from {persona_guid}: {first_memory.guid}")
                await bridge.runtime.api.character_memory_remove(
                    persona_guid, first_memory.guid
                )

            # Clear all memories - if there aren't any, an exception will be thrown
            if len(old_memories.memories) > 1:
                print(f"Clearing all memories for {persona_guid}")
                await bridge.runtime.api.character_memory_clear(persona_guid)

            # Add new memories to the character, effectively replacing their old memories with new ones
            print(f"Adding memory to {persona_guid}")
            memory_0 = await bridge.runtime.api.character_memory_add(
                persona_guid=persona_guid,
                timestamp=str(bridge.runtime.start_date - timedelta(days=260)),
                summary="Sheriff Morgan, Rose's father was murdered. I'm the new sheriff now. I secretly love her, but"
                " I'm not sure she feels the same way, especially since she's been grieving and I haven't"
                " found the killer yet. The case has gone cold and we'll probably never know who did it.",
                entity_ids=[persona_guid, "rose_morgan"],
                importance_weight=10,
            )
            print(f"Memory added: {memory_0}")

            print(f"Adding memory to {persona_guid}")
            memory_1 = await bridge.runtime.api.character_memory_add(
                persona_guid=persona_guid,
                timestamp=str(bridge.runtime.start_date - timedelta(hours=1)),
                summary="The Body was found just outside of town. Someone left a note on my desk, but I don't know "
                "who it was from.",
                entity_ids=[persona_guid, "dead_native"],
                importance_weight=10,
            )
            print(f"Memory added: {memory_1}")

            print(f"Focusing {persona_guid}")
            await bridge.runtime.api.focus_character(
                persona_guid, bridge.runtime.api.FocusPanelTab.HISTORY
            )

            print(f"Following {persona_guid} with the camera")
            await bridge.runtime.api.follow_character(persona_guid, 0.8)

            future = asyncio.get_event_loop().create_future()
            await bridge.runtime.api.modal(
                f"Memories Updated",
                f"{persona_guid}'s memories were replaced with new ones. See the History panel to the left to inspect them.",
                ["Ok"],
                True,
                future=future,
            )
            await future

            # Resume simulation
            return True

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class FocusCharacter(Demo):
    def __init__(self):
        super().__init__(
            name="Focus Character",
            summary="Focus the simulation on Jack Kane",
            category=CATEGORY,
            function=self.focus_character_demo,
        )

    def focus_character_demo(self, bridge: RuntimeBridge):
        """
        Focus on Jack Kane, follow him, then remove focus after 10 simulation ticks.
        When a character is focused:
            * The character details UI appears in the top-left corner.
            * Their current navigation path is highlighted.
            * The player can take actions on behalf of the character by selecting other objects in
              the Runtime and choosing an option from their context menu.
            * Their name tag and chat bubble is always visible along with any other conversation partners.

        API calls:
            focus_character()
            follow_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        persona_guid = "jack_kane"
        tick_count = 0

        # Focus on and follow the character at simulation start
        async def on_ready(_, world_context: WorldContextObject) -> bool:

            await disable_all_agents(bridge, world_context)

            print(f"Focusing {persona_guid} and opening the character details panel")
            await bridge.runtime.api.focus_character(
                persona_guid, bridge.runtime.api.FocusPanelTab.CHARACTER_DETAILS
            )

            print(f"Following {persona_guid} with the camera")
            await bridge.runtime.api.follow_character(persona_guid, 0.8)

            # Show the user a description of the focus command
            future = asyncio.get_event_loop().create_future()
            await bridge.runtime.api.modal(
                f"Focused on {persona_guid}",
                f"When a character is focused:\n"
                f"\t* The character details UI appears in the top-left corner.\n"
                f"\t* Their current navigation path is highlighted.\n"
                f"\t* The player can take actions on behalf of the character by selecting other objects in the Runtime and choosing an option from their context menu.\n"
                f"\t* Their name tag and chat bubble is always visible along with any other conversation partners.\n\n"
                f"After 10 seconds, the character will automatically be un-focused.\n"
                f"To un-focus a character manually, press the Escape key or right-click the mouse.\n",
                ["OK"],
                True,
                future=future,
            )
            # Wait for the user to press OK
            await future

            return True

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready

        # Stop focusing the character after 10 simulation ticks
        async def on_tick(_, now: datetime):
            nonlocal tick_count, persona_guid
            tick_count += 1
            if tick_count == 10:
                print(f"Removing focus from {persona_guid}")
                await bridge.runtime.api.focus_character("")

        print("Registering custom on_tick callback.")
        bridge.on_tick = on_tick

        async def on_character_focused(_: RuntimeBridge, persona_guid_: str):
            print(f"{persona_guid_} was focused")

        print("Registering custom on_character_focused callback.")
        bridge.on_character_focused = on_character_focused

        async def on_character_unfocused(_: RuntimeBridge, persona_guid_: str):
            print(f"{persona_guid_} was unfocused")

        print("Registering custom on_character_unfocused callback.")
        bridge.on_character_unfocused = on_character_unfocused


class OverrideCharacterAction(Demo):
    def __init__(self):
        super().__init__(
            name="Override Character Action",
            summary="Force Jack Kane to hide the dead body in the Saloon storage room",
            category=CATEGORY,
            function=self.override_character_action_demo,
        )

    def override_character_action_demo(self, bridge: RuntimeBridge):
        """
        On simulation start, Jack Kane uses the 'take_to' skill to navigate to the dead body, pick it up, carry it
        to the Saloon storage room, and place it on the ground.

        API calls:
            get_character_context()
            override_character_action()
            follow_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        persona_guid = "jack_kane"

        async def on_ready(_, world_context: WorldContextObject) -> bool:

            await disable_all_agents(bridge, world_context)

            take_to_action = TakeToSkill(
                guid="dead_body",
                destination="saloon_storage_room",
                goal="Dispose of the evidence",
            ).to_action()

            print(f"Overriding action for {persona_guid} with {take_to_action}")
            await bridge.runtime.api.override_character_action(
                persona_guid, take_to_action
            )

            print(f"Following {persona_guid} with the camera")
            await bridge.runtime.api.follow_character(persona_guid, 0.8)

            return True

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class RobBankAndArrestCriminal(Demo):
    def __init__(self):
        super().__init__(
            name="Rob Bank and Arrest Criminal",
            summary="Force Jack Kane to rob the bank and get arrested by Wyatt Cooper",
            category=CATEGORY,
            function=self.rob_bank_arrest_criminal_demo,
        )

    def rob_bank_arrest_criminal_demo(self, bridge: RuntimeBridge):
        """
        On simulation start, the Jack Kane navigates to the bank, steals the gold, and attempts to hide the gold
        in an alleyway. After 60 minutes of elapsed simulation time (60 seconds realtime), Wyatt Cooper arrests Kane
        and escorts him to the jail cell. Kane's character context is used to find the interactable 'bank' object
        which contains the 'Rob Bank' interaction. Likewise, Cooper's context is used to find the 'Arrest Person'
        interaction on Kane. These interactions are then used to construct an action that uses the 'interact' skill.

        API calls:
            get_character_context()
            override_character_action()
            follow_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        sheriff_id = "wyatt_cooper"
        robber_id = "jack_kane"
        arrest_triggered = False
        arrest_time: datetime

        async def on_ready(_, world_context: WorldContextObject) -> bool:
            nonlocal robber_id, arrest_time

            await disable_all_agents(bridge, world_context)

            # Arrest the robber 60 minutes after the simulation starts
            # This time span helps ensure that the robbery happens before the arrest
            arrest_time = bridge.runtime.start_date + timedelta(minutes=60)

            print(f"Getting character context for {robber_id}")
            context = await bridge.runtime.api.get_character_context(robber_id)

            # context.interactables is a list of all world objects/characters with interactions available
            interactable_bank = next(
                i for i in context.interactables if i.guid == "bank"
            )
            rob_bank_interaction_name = next(
                name for name in interactable_bank.interactions if "Rob" in name
            )

            interact_action = InteractSkill(
                guid=interactable_bank.guid,
                interaction=rob_bank_interaction_name,
                goal="Steal gold from the bank",
            ).to_action()

            print(f"Force {robber_id} to rob the bank using action:\n{interact_action}")
            await bridge.runtime.api.override_character_action(
                robber_id, interact_action
            )

            print(f"Following {robber_id} with the camera")
            await bridge.runtime.api.follow_character(robber_id, 0.8)

            return True

        async def on_tick(_, current_time: datetime):
            nonlocal arrest_triggered, robber_id, arrest_time
            # Only trigger the arrest once at the designated time
            if arrest_triggered or current_time < arrest_time:
                return

            arrest_triggered = True

            print(f"Getting character context for {sheriff_id}")
            context = await bridge.runtime.api.get_character_context(sheriff_id)

            # context.interactables is a list of all world objects/characters with interactions available
            interactable_robber = next(
                i for i in context.interactables if i.guid == robber_id
            )
            arrest_interaction_name = next(
                name for name in interactable_robber.interactions if "Arrest" in name
            )

            interact_action = InteractSkill(
                guid=interactable_robber.guid,
                interaction=arrest_interaction_name,
                goal="Arrest the bank robber",
            ).to_action()

            print(
                f"Force {sheriff_id} to arrest {robber_id} using action:\n{interact_action}"
            )
            await bridge.runtime.api.override_character_action(
                sheriff_id, interact_action
            )

        print("Registering custom on_ready and on_tick callbacks.")
        bridge.on_ready = on_ready
        bridge.on_tick = on_tick


class CustomConversation(Demo):
    def __init__(self):
        super().__init__(
            name="Custom Conversation",
            summary="Provide custom dialogue for Jack Kane and Razor Donovan",
            category=CATEGORY,
            function=self.custom_conversation_demo,
        )

    def custom_conversation_demo(self, bridge: RuntimeBridge):
        """
        Jack Kane and Razor Donovan carry out a custom pre-generated conversation. On simulation start, the camera begins following
        Kane, they navigate towards each other, and then they exchange the given dialogue lines.
        A custom action is used to trigger the conversation using the 'converse_with' skill.

        API calls:
            override_character_action()
            follow_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        speaker_1_id = "jack_kane"
        speaker_2_id = "razor_donovan"

        async def on_ready(_, world_context: WorldContextObject) -> bool:

            await disable_all_agents(bridge, world_context)

            conversation = [
                {
                    "persona_guid": speaker_1_id,
                    "dialogue": "Did you hear about the murder last night?",
                },
                {"persona_guid": speaker_2_id, "dialogue": "What?! Who was killed?"},
                {
                    "persona_guid": speaker_1_id,
                    "dialogue": "I don't know, but this isn't a good look for the town. We're developing a reputation.",
                },
                {
                    "persona_guid": speaker_2_id,
                    "dialogue": "I'm gonna stock up on ammunition. This place is getting dangerous.'",
                },
            ]

            print(f"Starting conversation between {speaker_1_id} and {speaker_2_id}:")
            for turn in conversation:
                speaker = turn.get("persona_guid")
                dialogue = turn.get("dialogue")
                print(f"\t{speaker}: {dialogue}")

            # Construct a custom converse_with action
            converse_with_action = ConverseWithSkill(
                persona_guid=speaker_2_id,  # The conversation companion - in this example speaker_1 is the initiator and speaker_2 is the companion
                conversation=conversation,  # If no conversation is provided, one will be generated instead
                topic="the murder last night",
                context="",  # Only required if no conversation is provided
                goal="Discuss the recent murder",
            ).to_action()

            # Force the characters to converse immediately
            await bridge.runtime.api.override_character_action(
                speaker_1_id, converse_with_action
            )

            print(f"Following {speaker_1_id} with the camera")
            await bridge.runtime.api.follow_character(speaker_1_id, 0.8)

            return True

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class PlaceCharacter(Demo):
    def __init__(self):
        super().__init__(
            name="Place Character",
            summary="Move Jack Kane to a specific location in the scene",
            category=CATEGORY,
            function=self.place_character_demo,
        )

    def place_character_demo(self, bridge: RuntimeBridge):
        """
        Instantly warp Jack Kane to the chosen location and follow him with the camera.

        API calls:
            get_world_context()
            modal()
            place_character()
            follow_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        persona_guid = "jack_kane"
        world_context_: WorldContextObject
        location_options_ = []
        tick_count_ = -1

        async def on_ready(_, world_context: WorldContextObject) -> bool:

            nonlocal world_context_, location_options_

            await disable_all_agents(bridge)

            # Force the placed character to stop navigating and idle forever
            await bridge.runtime.api.override_character_action(
                persona_guid,
                WaitSkill(
                    duration=0,
                    goal=f"Force {persona_guid} to idle forever",
                ).to_action(),
            )

            # Store a list of location names for use with the modal
            world_context_ = world_context
            location_options_ = [location.name for location in world_context_.locations]

            # Start the simulation
            return True

        async def on_tick(_, current_time: datetime):

            nonlocal tick_count_

            # Choose a new location every 5 ticks
            tick_count_ += 1
            if tick_count_ % 5 != 0:
                return

            # Allow player to choose new location in Runtime
            future = asyncio.get_event_loop().create_future()
            await bridge.runtime.api.modal(
                f"Choose a Location",
                f"Place {persona_guid} at the following location:",
                location_options_,
                True,
                future=future,
            )
            modal_response = await future

            # Retrieve the chosen location
            choice_idx = modal_response["choice"]
            location_name = location_options_[choice_idx]
            location = next(
                loc for loc in world_context_.locations if loc.name == location_name
            )

            print(
                f"Placing {persona_guid} at '{location_name}' with position {location.center_floor_position}"
            )
            await bridge.runtime.api.place_character(
                persona_guid, location.center_floor_position, Vector3(0, 90, 0)
            )

            print(f"Following {persona_guid} with the camera")
            await bridge.runtime.api.follow_character(persona_guid, 0.8)

            return True

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready
        print("Registering custom on_tick callback.")
        bridge.on_tick = on_tick
