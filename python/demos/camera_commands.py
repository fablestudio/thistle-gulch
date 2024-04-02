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


class PlaceCamera(Demo):
    def __init__(self):
        super().__init__(
            name="Place Camera",
            description="Place the camera in the scene with a specific position, rotation, and field of view",
            category=CATEGORY,
            function=self.place_camera_demo,
        )

    def place_camera_demo(self, bridge: RuntimeBridge):

        position_x = float(input("Enter camera position X in meters: "))
        position_y = float(input("Enter camera position Y in meters: "))
        position_z = float(input("Enter camera position Z in meters: "))
        rotation_x = float(input("Enter camera rotation X in degrees (+/-360): "))
        rotation_y = float(input("Enter camera rotation Y in degrees (+/-360): "))
        rotation_z = float(input("Enter camera rotation Z in degrees (+/-360): "))
        field_of_view = float(input("Enter camera field of view in degrees (5-120): "))

        # Place the camera at simulation start
        async def on_ready(_):
            print(
                f"Placing camera at \n\tposition: {position_x, position_y, position_z}\n\trotation: {rotation_x, rotation_y, rotation_z}\n\tfov: {field_of_view}"
            )
            await bridge.runtime.api.place_camera(
                position_x,
                position_y,
                position_z,
                rotation_x,
                rotation_y,
                rotation_z,
                field_of_view,
            )

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready
