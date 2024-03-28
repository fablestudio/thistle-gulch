from datetime import datetime
from time import sleep

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

        datestr = input("Enter the start hour (HH - 24hour): ")
        date = datetime(1880, 1, 1, int(datestr))

        async def on_ready(_):
            print(f"Current simulation start time is {bridge.runtime.start_date}")
            print(f"Setting simulation start time to {date}")
            await bridge.runtime.api.set_start_date(date)

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready


class SimulationTickDemo(Demo):
    def __init__(self):
        super().__init__(
            name="Simulation Tick",
            description="Pause the simulation for the given number of seconds on every tick",
            category=CATEGORY,
            function=self.on_simulation_tick,
        )

    def on_simulation_tick(self, bridge: RuntimeBridge):
        """
        Pause the simulation for the given number of seconds on every tick

        :param bridge: The bridge to the runtime.
        """

        seconds = int(input("Enter number of seconds to wait between ticks: "))

        async def on_tick(_, current_time: datetime):
            print(f"Current simulation time is {current_time}")
            print(f"Pausing simulation and waiting for {seconds} seconds")
            await bridge.runtime.api.pause()
            sleep(seconds)
            await bridge.runtime.api.resume()

        print("Registering custom on_tick callback.")
        bridge.on_tick = on_tick
