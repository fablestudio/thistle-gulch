import asyncio
from datetime import datetime
from time import sleep

from thistle_gulch.bridge import RuntimeBridge
from thistle_gulch.data_models import Vector3, WorldContextObject
from . import (
    Demo,
    formatted_input_async,
    choose_from_list,
    disable_all_agents,
    formatted_input,
)

CATEGORY = "Camera Commands"


class FollowCharacter(Demo):
    def __init__(self):
        super().__init__(
            name="Follow Character",
            summary="Follow Jack Kane with the camera",
            category=CATEGORY,
            function=self.follow_character_demo,
        )

    def follow_character_demo(self, bridge: RuntimeBridge):
        """
        Follow a specific character with the camera, then stop following after 10 simulation ticks.
        The camera will track the character as they walk around the world until the player manually moves the camera
        with WASD, presses ESC, left-clicks another object, or right-clicks anywhere in the screen. A followed
        character's name tag and chat bubble is always visible along with any other conversation partners.

        API calls:
            follow_character()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/camera_commands.py
        """

        persona_guid = "jack_kane"

        def validate_zoom(zoom_str: str) -> float:
            zoom_val = float(zoom_str)
            if zoom_val < 0 or zoom_val > 1:
                raise ValueError(f"Zoom value must be between 0.0 and 1.0")
            return zoom_val

        zoom = formatted_input(
            "Enter camera zoom amount between 0.0 (furthest) and 1.0 (closest)",
            validator=validate_zoom,
        )

        # Follow the character at simulation start
        async def on_ready(_, world_context: WorldContextObject) -> bool:

            await disable_all_agents(bridge, world_context)

            print(f"Following {persona_guid} with the camera")
            await bridge.runtime.api.follow_character(persona_guid, zoom)

            # Start the simulation
            return True

        tick_count = 0

        # Stop following the character after 10 simulation ticks
        async def on_tick(_, now: datetime):
            nonlocal tick_count, persona_guid
            tick_count += 1
            if tick_count == 10:
                print(f"Stop following {persona_guid}")
                await bridge.runtime.api.follow_character("", 0)

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready
        bridge.on_tick = on_tick


class PlaceCamera(Demo):
    def __init__(self):
        super().__init__(
            name="Place Camera",
            summary="Place the camera in the scene",
            category=CATEGORY,
            function=self.place_camera_demo,
        )

    def place_camera_demo(self, bridge: RuntimeBridge):
        """
        Place the camera in the scene with a specific position, rotation, and field of view. This temporarily switches
        to the "God" camera mode - Press ESC or click anywhere in the screen to restore the default camera mode.

        API calls:
            place_camera()

        See the API and Demo source code on Github for more information:
            https://github.com/fablestudio/thistle-gulch/blob/main/python/thistle_gulch/api.py
            https://github.com/fablestudio/thistle-gulch/blob/main/python/demos/camera_commands.py
        """

        # Camera position
        def validate_position(pos_str: str) -> float:
            pos = float(pos_str)
            return pos

        print("NOTE: Just press enter to use the default values of a saloon camera.")

        position_x = formatted_input(
            "Enter camera position X in meters",
            validator=validate_position,
            default="18.14",
        )
        position_y = formatted_input(
            "Enter camera position Y in meters",
            validator=validate_position,
            default="3.55",
        )
        position_z = formatted_input(
            "Enter camera position Z in meters",
            validator=validate_position,
            default="-8.26",
        )

        # Camera rotation
        def validate_rotation(rot_str: str) -> float:
            rot = float(rot_str)
            if rot < -360 or rot > 360:
                raise ValueError(f"Rotation value must be between -360.0 and 360.0")
            return rot

        rotation_x = formatted_input(
            "Enter camera rotation X in degrees (+/-360.0)",
            validator=validate_rotation,
            default="10.81",
        )
        rotation_y = formatted_input(
            "Enter camera rotation Y in degrees (+/-360.0)",
            validator=validate_rotation,
            default="205.097",
        )
        rotation_z = formatted_input(
            "Enter camera rotation Z in degrees (+/-360.0)",
            validator=validate_rotation,
            default="0",
        )

        # Camera field of view
        def validate_fov(fov_str: str) -> float:
            fov = float(fov_str)
            if fov < 5 or fov > 120:
                raise ValueError(f"Field of view must be between 5 and 120")
            return fov

        field_of_view = formatted_input(
            "Enter camera field of view in degrees (5-120)",
            validator=validate_fov,
            default="13.1",
        )

        # Place the camera at simulation start
        async def on_ready(_, world_context: WorldContextObject) -> bool:

            await disable_all_agents(bridge, world_context)

            print(
                f"Placing camera at \n"
                f"\tposition: {position_x, position_y, position_z}\n"
                f"\trotation: {rotation_x, rotation_y, rotation_z}\n\tfov: {field_of_view}"
            )
            await bridge.runtime.api.place_camera(
                Vector3(position_x, position_y, position_z),
                Vector3(rotation_x, rotation_y, rotation_z),
                field_of_view,
            )

            future = asyncio.get_event_loop().create_future()
            await bridge.runtime.api.modal(
                f"Custom camera",
                f"The camera was placed with a custom position and rotation. To exit this mode, press the camera icon "
                f"on the lower left side of the screen.",
                ["OK"],
                True,
                future=future,
            )
            await future

            # Start the simulation
            return True

        print("Registering custom on_ready callback.")
        bridge.on_ready = on_ready
