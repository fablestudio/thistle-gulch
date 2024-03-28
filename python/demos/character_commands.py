from datetime import datetime, timedelta
from thistle_gulch.bridge import RuntimeBridge
from . import Demo

CATEGORY = "Character Commands"


class EnableAgentDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Enable Agent",
            description="Enable or disable an agent after the simulation has started. An enabled agent uses the python bridge to generate its actions.",
            category=CATEGORY,
            function=self.enable_agent_demo,
        )

    def enable_agent_demo(self, bridge: RuntimeBridge):
        """
        Enable or disable an agent

        :param bridge: The bridge to the runtime.
        """

        persona_id = input("Enter persona id: ")
        enable_str = input("Enable(1) or Disable(0) the agent? ")
        enabled = True if enable_str == "1" else False

        async def on_ready(_):
            print(f"{('Enabling' if enabled else 'Disabling')} agent: {persona_id}")
            await bridge.runtime.api.enable_agent(persona_id, enabled)

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class UpdateCharacterPropertyDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Update Character Property",
            description="Change a property value for the given persona",
            category=CATEGORY,
            function=self.update_character_property,
        )

    def update_character_property(self, bridge: RuntimeBridge):
        """
        Change a property value for the given persona

        :param bridge: The bridge to the runtime.
        """

        persona_id = input("Enter persona id: ")
        property_name = input(
            "Enter property name (energy, summary, description, backstory): "
        )
        property_value = input(f"Enter new value for {property_name}: ")

        async def on_ready(_):
            print(f"Updating {persona_id} {property_name} to '{property_value}'")
            await bridge.runtime.api.update_character_property(
                persona_id, property_name, property_value
            )

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class OverrideCharacterAction(Demo):
    def __init__(self):
        super().__init__(
            name="Override Character Action",
            description="Manually trigger a specific action for a character",
            category=CATEGORY,
            function=self.override_character_action_demo,
        )

    def override_character_action_demo(self, bridge: RuntimeBridge):
        """
        Manually trigger a specific action for a character

        :param bridge: The bridge to the runtime.
        """

        persona_id = input("Enter persona id: ")

        async def on_ready(_):
            print(f"Getting character context for {persona_id}")
            context = await bridge.runtime.api.get_character_context(persona_id)
            location = context.locations[0]

            action = {
                "skill": "go_to",
                "parameters": {
                    "destination": location.name,
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
            description="Force a character to rob the bank and get arrested by the sheriff",
            category=CATEGORY,
            function=self.rob_bank_arrest_criminal_demo,
        )
        self.arrest_triggered = False
        self.arrest_time: datetime

    def rob_bank_arrest_criminal_demo(self, bridge: RuntimeBridge):
        """
        Force a character to rob the bank and get arrested by sheriff wyatt_cooper

        :param bridge: The bridge to the runtime.
        """

        robber_id = input("Enter persona id to rob the bank: ")

        async def on_ready(_):
            self.arrest_time = bridge.runtime.start_date + timedelta(hours=1)

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
            print(f"Force {robber_id} to rob the bank")
            await bridge.runtime.api.override_character_action(robber_id, action)

        async def on_tick(_, current_time: datetime):
            # Only trigger the arrest once at the designated time
            if self.arrest_triggered or current_time < self.arrest_time:
                return

            self.arrest_triggered = True

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
            print(f"Force wyatt_cooper to arrest {robber_id}")
            await bridge.runtime.api.override_character_action("wyatt_cooper", action)

        print("Registering custom on_ready and on_tick callbacks.")
        bridge.on_ready = on_ready
        bridge.on_tick = on_tick
