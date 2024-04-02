from datetime import datetime
from time import sleep

from thistle_gulch.bridge import RuntimeBridge
from . import Demo

CATEGORY = "Camera Commands"


class FollowCharacter(Demo):
    def __init__(self):
        super().__init__(
            name="Follow Character",
            description="Follow a specific character with the camera, then stop following after 10 simulation ticks",
            category=CATEGORY,
            function=self.follow_character_demo,
        )

    def follow_character_demo(self, bridge: RuntimeBridge):
        """
        Follow a specific character with the camera

        :param bridge: The bridge to the runtime.
        """

        persona_id = input("Enter persona id: ")
        zoom = float(
            input("Enter camera zoom amount between 0.0 (furthest) and 1.0 (closest): ")
        )

        # Follow the character at simulation start
        async def on_ready(_):
            print(f"Following {persona_id} with the camera")
            await bridge.runtime.api.follow_character(persona_id, zoom)

        tick_count = 0

        # Stop following the character after 10 simulation ticks
        async def on_tick(_, now: datetime):
            nonlocal tick_count
            tick_count += 1
            if tick_count == 10:
                print(f"Stop following {persona_id}")
                await bridge.runtime.api.follow_character("", 0)

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready
        bridge.on_tick = on_tick
