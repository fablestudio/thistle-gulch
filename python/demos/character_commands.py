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
            description="Manually trigger a specific action for an NPC",
            category=CATEGORY,
            function=self.override_character_action_demo,
        )

    def override_character_action_demo(self, bridge: RuntimeBridge):
        """
        Manually trigger a specific action for an NPC

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
