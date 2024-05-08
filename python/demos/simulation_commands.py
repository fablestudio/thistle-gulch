import asyncio
from datetime import datetime
from time import sleep
from typing import Optional

from thistle_gulch.bridge import RuntimeBridge
from thistle_gulch.data_models import WorldContextObject, Persona, SimObject
from . import Demo, disable_all_agents

CATEGORY = "Simulation Commands"


class SetStartTimeDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Set Start Time",
            summary="Set the start time of the simulation",
            category=CATEGORY,
            function=self.set_start_time_demo,
        )

    def set_start_time_demo(self, bridge: RuntimeBridge):
        """
        On simulation start, a new start date is assigned which determines the "Day 1" for the simulation clock.
        The scene lighting and environment also update to match the time of day. The start date must be set in the
        on_ready callback - attempting to set it in the on_tick callback will result in an error. The current start
        date is accessible via the Runtime class.

        API calls:
            set_start_date()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/simulation_commands.py
        """

        datestr = input("Enter the start hour (HH - 24hour): ")
        date = datetime(1880, 1, 1, int(datestr))

        async def on_ready(_, world_context: WorldContextObject) -> bool:

            await disable_all_agents(bridge, world_context)

            print(f"Current simulation start time is {bridge.runtime.start_date}")
            print(f"Setting simulation start time to {date}")
            await bridge.runtime.api.set_start_date(date)
            return True

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class SimulationTickDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Simulation Tick",
            summary="Demonstrates basic usage of the bridge.on_tick() callback",
            category=CATEGORY,
            function=self.on_simulation_tick,
        )

    def on_simulation_tick(self, bridge: RuntimeBridge):
        """
        On every simulation tick, the simulation is paused by the Bridge for the given number of seconds and then
        resumed to simulate a long-running process. While paused, the Runtime time controls are disabled and the
        simulation can only be un-paused by sending a 'resume' command from the Bridge.

        API calls:
            pause()
            resume()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/simulation_commands.py
        """

        async def on_ready(_, world_context: WorldContextObject) -> bool:
            await disable_all_agents(bridge, world_context)
            return True

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready

        seconds = int(input("Enter number of seconds to wait between ticks: "))

        async def on_tick(_, current_time: datetime):
            print(f"Current simulation time is {current_time}")
            print(f"Pausing simulation and waiting for {seconds} seconds")
            await bridge.runtime.api.pause()
            sleep(seconds)
            await bridge.runtime.api.resume()

        print("Registering custom on_tick callback.")
        bridge.on_tick = on_tick


class SelectSimObject(Demo):
    def __init__(self):
        super().__init__(
            name="Select Sim Object",
            summary="Detect character and sim_object selections and print their associated data",
            category=CATEGORY,
            function=self.select_sim_object_demo,
        )

    def select_sim_object_demo(self, bridge: RuntimeBridge):
        """
        When a character or sim_object is selected in the Runtime using the mouse, the bridge.on_sim_object_selected()
        callback is used to find the associated object in the world context and its data is printed to the console.

        API calls:
            get_world_context()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/simulation_commands.py
        """

        world_context_: WorldContextObject

        # Focus on and follow the character at simulation start
        async def on_ready(_, world_context: WorldContextObject) -> bool:
            nonlocal world_context_

            await disable_all_agents(bridge, world_context)

            world_context_ = world_context

            # Show the user a description of how object selection works
            future = asyncio.get_event_loop().create_future()
            await bridge.runtime.api.modal(
                f"Object Selection",
                f"Use the mouse to select any character or object in the scene. An object is selectable if a tooltip "
                f"appears when hovering the mouse over them.\n\nWhen selected, the bridge.on_sim_object_selected() "
                f"callback will print their details in the python console.",
                ["OK"],
                True,
                future=future,
            )
            # Wait for the user to press OK
            await future

            # Don't start the simulation
            return False

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready

        async def on_sim_object_selected(_: RuntimeBridge, guid: str):
            print(f"\n{guid} was selected")

            # Check if the selected object was a character
            selected_object: Optional[Persona | SimObject] = next(
                (p for p in world_context_.personas if p.persona_guid == guid), None
            )

            # Otherwise look for a sim object
            if selected_object is None:
                selected_object = next(
                    (s for s in world_context_.sim_objects if s.guid == guid), None
                )

            # Object not found
            if selected_object is None:
                print(
                    f"Failed to find persona or sim_object in world context with id: '{guid}'"
                )
            # Print the object data to the console
            else:
                print(f"Selected object data:\n{selected_object}")

        print("Registering custom on_character_focused callback.")
        bridge.on_sim_object_selected = on_sim_object_selected
