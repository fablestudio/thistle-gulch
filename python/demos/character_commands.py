from datetime import datetime, timedelta
from thistle_gulch.bridge import RuntimeBridge
from . import Demo, choose_from_list, get_persona_list, formatted_input_async

CATEGORY = "Character Commands"


# noinspection PyAttributeOutsideInit
class EnableAgentDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Enable Agent",
            summary="Enable or disable an agent after the simulation has started. An enabled agent uses the python bridge to generate its actions.",
            category=CATEGORY,
            function=self.enable_agent_demo,
        )

    def enable_agent_demo(self, bridge: RuntimeBridge):
        """
        Enable or disable an agent

        :param bridge: The bridge to the runtime.
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
        Change a property value for the given persona

        :param bridge: The bridge to the runtime.
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
                "Enter property name (energy, summary, description, backstory): ",
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

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class OverrideCharacterAction(Demo):
    def __init__(self):
        super().__init__(
            name="Override Character Action",
            summary="Manually trigger a specific GOTO action for a character",
            category=CATEGORY,
            function=self.override_character_action_demo,
        )

    def override_character_action_demo(self, bridge: RuntimeBridge):
        """
        Force a character to go to the first available world location

        :param bridge: The bridge to the runtime.
        """

        async def on_ready(_):

            persona_list = await get_persona_list(bridge)
            persona_id = await choose_from_list("Enter persona id", persona_list)

            print(f"Getting character context for {persona_id}")
            context = await bridge.runtime.api.get_character_context(persona_id)

            location_id = await choose_from_list(
                "Pick a location_id for this persona to go to:",
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
        Force a character to rob the bank and get arrested by sheriff wyatt_cooper

        :param bridge: The bridge to the runtime.
        """

        robber_id: str
        arrest_triggered = False
        arrest_time: datetime

        async def on_ready(_):
            nonlocal robber_id, arrest_time
            persona_list = await get_persona_list(bridge)
            # Choose the persona to rob the bank, excluding wyatt_cooper since he will arrest the robber.
            robber_id = await choose_from_list(
                "Enter persona id to rob the bank",
                persona_list,
                exclude=["wyatt_cooper"],
            )

            # Arrest the robber 10 minutes after the simulation starts
            arrest_time = bridge.runtime.start_date + timedelta(minutes=10)

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

        async def on_tick(_, current_time: datetime):
            nonlocal arrest_triggered, robber_id, arrest_time
            # Only trigger the arrest once at the designated time
            if arrest_triggered or current_time < arrest_time:
                return

            arrest_triggered = True

            print(f"Getting character context for wyatt_cooper")
            context = await bridge.runtime.api.get_character_context("wyatt_cooper")

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
            print(f"Force wyatt_cooper to arrest {robber_id} using action:\n{action}")
            await bridge.runtime.api.override_character_action("wyatt_cooper", action)

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
        Provide custom dialogue for a set characters to perform
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

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready
