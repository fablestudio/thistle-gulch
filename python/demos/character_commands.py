from datetime import datetime, timedelta
from thistle_gulch.bridge import RuntimeBridge
from . import Demo, choose_from_list, get_persona_list, formatted_input_async

CATEGORY = "Character Commands"


# noinspection PyAttributeOutsideInit
class EnableAgentDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Enable Agent",
            summary="Enable or disable an agent",
            category=CATEGORY,
            function=self.enable_agent_demo,
        )

    def enable_agent_demo(self, bridge: RuntimeBridge):
        """
        On simulation start, the chosen character's bridge agent is enabled or disabled. Enabled agents use the
        Bridge to generate their actions and will contribute to the overall cost of running the simulation. Disabled
        agents choose their actions directly in the simulation Runtime using a simple scoring system instead of sending
        requests to the Bridge.

        API calls:
            enable_agent()
            follow_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        async def on_ready(_):
            persona_list = await get_persona_list(bridge)
            persona_id = await choose_from_list("Enter persona id", persona_list)

            # Validate that the user entered 0 or 1
            def validate_enable_str(enable_str: str) -> bool:
                if enable_str not in ["0", "1"]:
                    raise ValueError(
                        f"Invalid option {enable_str}. Please enter 0 or 1."
                    )
                return True if enable_str == "1" else False

            enabled = await formatted_input_async(
                "Enable(1) or Disable(0) the agent? ", validator=validate_enable_str
            )

            print(f"{('Enabling' if enabled else 'Disabling')} agent: {persona_id}")
            await bridge.runtime.api.enable_agent(persona_id, enabled)

            print(f"Following {persona_id} with the camera")
            await bridge.runtime.api.follow_character(persona_id, 0.8)

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class UpdateCharacterPropertyDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Update Character Property",
            summary="Change a property value for the given persona",
            category=CATEGORY,
            function=self.update_character_property,
        )

    def update_character_property(self, bridge: RuntimeBridge):
        """
        On simulation start, the chosen character's property is updated to the value provided. The character's agent
        may optionally be enabled which is useful for seeing the effect of the new value during action and conversation
        generation. The character is also focused for ease of access to the character details UI to inspect the changes.
        The currently available properties are energy, summary, description, and backstory, but this list will continue
        to expand in the future.

        API calls:
            update_character_property()
            enable_agent()
            follow_character()
            focus_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        async def on_ready(_):
            persona_list = await get_persona_list(bridge)
            persona_id = await choose_from_list("Enter persona id", persona_list)
            print()

            def validate_property_name(property_name: str) -> str:
                if property_name not in [
                    "energy",
                    "summary",
                    "description",
                    "backstory",
                ]:
                    raise ValueError(f"Invalid property name: {property_name}")
                return property_name

            property_name = await formatted_input_async(
                "Enter property name (energy, summary, description, backstory)",
                validator=validate_property_name,
            )

            property_value = await formatted_input_async(
                f"Enter new value for {property_name}"
            )

            print(f"Updating {persona_id} {property_name} to '{property_value}'")
            await bridge.runtime.api.update_character_property(
                persona_id, property_name, property_value
            )

            enable_agent = await formatted_input_async(
                "Do you want to enable this agent as well? (Y/n)", default="Y"
            )
            if enable_agent.lower() == "y":
                print(f"Enabling Agent: {persona_id}'")
                await bridge.runtime.api.enable_agent(persona_id, True)

            print(f"Focusing {persona_id}")
            await bridge.runtime.api.focus_character(persona_id)

            print(f"Following {persona_id} with the camera")
            await bridge.runtime.api.follow_character(persona_id, 0.8)

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class FocusCharacter(Demo):
    def __init__(self):
        super().__init__(
            name="Focus Character",
            summary="Focus the simulation on a specific character",
            category=CATEGORY,
            function=self.focus_character_demo,
        )

    def focus_character_demo(self, bridge: RuntimeBridge):
        """
        Focus a character, follow them, then remove focus after 10 simulation ticks.
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

        persona_id: str
        tick_count = 0

        # Focus on and follow the character at simulation start
        async def on_ready(_):
            nonlocal persona_id
            persona_list = await get_persona_list(bridge)
            persona_id = await choose_from_list("Enter persona id", persona_list)

            print(f"Focusing {persona_id}")
            await bridge.runtime.api.focus_character(persona_id)

            print(f"Following {persona_id} with the camera")
            await bridge.runtime.api.follow_character(persona_id, 0.8)

        # Stop focusing the character after 10 simulation ticks
        async def on_tick(_, now: datetime):
            nonlocal tick_count, persona_id
            tick_count += 1
            if tick_count == 10:
                print(f"Remove focus from {persona_id}")
                await bridge.runtime.api.focus_character("")

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready
        bridge.on_tick = on_tick


class OverrideCharacterAction(Demo):
    def __init__(self):
        super().__init__(
            name="Override Character Action",
            summary="Manually trigger a custom action for a character",
            category=CATEGORY,
            function=self.override_character_action_demo,
        )

    def override_character_action_demo(self, bridge: RuntimeBridge):
        """
        On simulation start, the chosen character immediately starts navigating to the chosen location using the go_to skill.
        The character context is utilized to discover all available locations before the character's action is triggered.

        API calls:
            get_character_context()
            override_character_action()
            follow_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        async def on_ready(_):

            persona_list = await get_persona_list(bridge)
            persona_id = await choose_from_list("Enter persona id", persona_list)

            print(f"Getting character context for {persona_id}")
            context = await bridge.runtime.api.get_character_context(persona_id)

            location_id = await choose_from_list(
                "Pick a location_id for this persona to go to",
                [loc.name for loc in context.locations],
            )

            action = {
                "skill": "go_to",
                "parameters": {
                    "destination": location_id,
                    "goal": "Visit the first available location",
                },
            }

            print(f"Overriding action for {persona_id} with {action}")
            await bridge.runtime.api.override_character_action(persona_id, action)

            print(f"Following {persona_id} with the camera")
            await bridge.runtime.api.follow_character(persona_id, 0.8)

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class RobBankAndArrestCriminal(Demo):
    def __init__(self):
        super().__init__(
            name="Rob Bank and Arrest Criminal",
            summary="Force a character to rob the bank and get arrested by the sheriff",
            category=CATEGORY,
            function=self.rob_bank_arrest_criminal_demo,
        )

    def rob_bank_arrest_criminal_demo(self, bridge: RuntimeBridge):
        """
        On simulation start, the robber character navigates to the bank, steals the gold, and attempts to hide the gold
        in an alleyway. After 60 minutes of elapsed simulation time (60 seconds realtime), wyatt_cooper arrests the robber
        and escorts them to the jail cell. The robber's character context is used to find the interactable 'bank' object
        which contains the 'Rob Bank' interaction. Likewise, wyatt_cooper's context is used to find the 'Arrest Person'
        interaction on the robber. These interactions are then used to construct an action that uses the 'interact' skill.

        API calls:
            get_character_context()
            override_character_action()
            follow_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        sheriff_id = "wyatt_cooper"
        robber_id: str
        arrest_triggered = False
        arrest_time: datetime

        async def on_ready(_):
            nonlocal robber_id, arrest_time
            persona_list = await get_persona_list(bridge)
            # Choose the persona to rob the bank, excluding the sheriff since he will arrest the robber.
            robber_id = await choose_from_list(
                "Enter persona id to rob the bank",
                persona_list,
                exclude=[sheriff_id],
            )

            # Arrest the robber 60 minutes after the simulation starts
            # This time span helps ensure that the robbery happens before the arrest
            arrest_time = bridge.runtime.start_date + timedelta(minutes=60)

            print(f"Getting character context for {robber_id}")
            context = await bridge.runtime.api.get_character_context(robber_id)

            # context.interactables is a list of all world objects/characters with interactions available
            interactable_bank = next(
                i for i in context.interactables if i.item_guid == "bank"
            )
            rob_bank_interaction_name = next(
                name for name in interactable_bank.interactions if "Rob" in name
            )

            action = {
                "skill": "interact",
                "parameters": {
                    "item_guid": interactable_bank.item_guid,
                    "interaction": rob_bank_interaction_name,
                    "goal": "Steal gold from the bank",
                },
            }
            print(f"Force {robber_id} to rob the bank using action:\n{action}")
            await bridge.runtime.api.override_character_action(robber_id, action)

            print(f"Following {robber_id} with the camera")
            await bridge.runtime.api.follow_character(robber_id, 0.8)

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
                i for i in context.interactables if i.item_guid == robber_id
            )
            arrest_interaction_name = next(
                name for name in interactable_robber.interactions if "Arrest" in name
            )

            action = {
                "skill": "interact",
                "parameters": {
                    "item_guid": interactable_robber.item_guid,
                    "interaction": arrest_interaction_name,
                    "goal": "Arrest the bank robber",
                },
            }
            print(f"Force {sheriff_id} to arrest {robber_id} using action:\n{action}")
            await bridge.runtime.api.override_character_action(sheriff_id, action)

        print("Registering custom on_ready and on_tick callbacks.")
        bridge.on_ready = on_ready
        bridge.on_tick = on_tick


class CustomConversation(Demo):
    def __init__(self):
        super().__init__(
            name="Custom Conversation",
            summary="Provide custom dialogue for a set characters to perform",
            category=CATEGORY,
            function=self.custom_conversation_demo,
        )

    def custom_conversation_demo(self, bridge: RuntimeBridge):
        """
        Two characters carry out a custom pre-generated conversation. On simulation start, the camera begins following
        the first character, both characters navigate towards each other, and then they exchange the given dialogue lines.
        A custom action is used to trigger the conversation using the converse_with skill.

        API calls:
            override_character_action()
            follow_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/character_commands.py
        """

        async def on_ready(_):
            personas = await get_persona_list(bridge)
            speaker_1_id = await choose_from_list(
                "Enter speaker 1 id", options=personas
            )
            speaker_2_id = await choose_from_list(
                "Enter speaker 2 id", options=personas
            )

            conversation = [
                {
                    "persona_id": speaker_1_id,
                    "dialogue": "Did you hear about the murder last night?",
                },
                {"persona_id": speaker_2_id, "dialogue": "What?! Who was killed?"},
                {
                    "persona_id": speaker_1_id,
                    "dialogue": "I don't know, but this isn't a good look for the town. We're developing a reputation.",
                },
                {
                    "persona_id": speaker_2_id,
                    "dialogue": "I'm gonna stock up on ammunition. This place is getting dangerous.'",
                },
            ]

            action = {
                "skill": "converse_with",
                "parameters": {
                    "persona_guid": speaker_2_id,  # The conversation companion - in this example speaker_1 is the initiator and speaker_2 is the companion
                    "conversation": conversation,  # If no conversation is provided, one will be generated instead
                    "topic": "the murder last night",
                    "context": "",  # Only required if no conversation is provided
                    "goal": "Discuss the recent murder",
                },
            }

            print(f"Starting conversation between {speaker_1_id} and {speaker_2_id}:")
            for turn in conversation:
                speaker = turn.get("persona_id")
                dialogue = turn.get("dialogue")
                print(f"\t{speaker}: {dialogue}")

            await bridge.runtime.api.override_character_action(speaker_1_id, action)

            print(f"Following {speaker_1_id} with the camera")
            await bridge.runtime.api.follow_character(speaker_1_id, 0.8)

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready
