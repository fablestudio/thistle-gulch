from datetime import datetime

from thistle_gulch.bridge import RuntimeBridge
from . import Demo

CATEGORY = "Simulation Commands"


class SetStartTimeDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Set Start Time",
            description="Set the start time of the simulation.",
            category=CATEGORY,
            function=self.set_start_time_demo,
        )

    def set_start_time_demo(self, bridge: RuntimeBridge):
        """
        Set the start time of the simulation.

        :param bridge: The bridge to the runtime.
        """

        datestr = input("Enter the start hour (HH - 24hour)")
        date = datetime(1880, 1, 1, int(datestr))

        async def on_ready(_):
            print(f"Setting the start time of the simulation to {date}")
            await bridge.runtime.api.set_start_date(date)

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class EnableAgentDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Enable Agent",
            description="Enable or disable an agent after the simulation has started",
            category=CATEGORY,
            function=self.enable_agent_demo,
        )

    def enable_agent_demo(self, bridge: RuntimeBridge):
        """
        Enable or disable an agent

        :param bridge: The bridge to the runtime.
        """

        persona_id = input("Enter persona id")
        enable_str = input("Enable(1) or Disable(0) the agent?")
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

        persona_id = input("Enter persona id")
        property_name = input(
            "Enter property name (energy, summary, description, backstory)"
        )
        property_value = input(f"Enter new value for {property_name}")

        async def on_ready(_):
            print(f"Updating {persona_id} {property_name} to '{property_value}'")
            await bridge.runtime.api.update_character_property(
                persona_id, property_name, property_value
            )

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready
