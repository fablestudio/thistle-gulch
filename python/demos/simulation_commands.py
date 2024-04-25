from datetime import datetime
from time import sleep

from thistle_gulch.bridge import RuntimeBridge
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

        async def on_ready(_) -> bool:

            await disable_all_agents(bridge)

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

        async def on_ready(_) -> bool:
            await disable_all_agents(bridge)
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
