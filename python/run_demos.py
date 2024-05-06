import logging
import sys
from typing import List

import fable_saga

import demos.custom_models as custom_models
import thistle_gulch
import thistle_gulch.bridge as tg_bridge
from demos import (
    Demo,
    override_actions,
    simulation_commands,
    character_commands,
    camera_commands,
    default_demos,
)


def main():
    # Run the bridge.
    bridge = tg_bridge.main(auto_run=False)

    # A list of available demos and the corresponding endpoint they override.
    options: List[Demo] = [
        default_demos.DefaultTutorial(),
        default_demos.MeetTheCharactersDemo(),
        override_actions.PrintActionsAndPickFirstDemo(),
        override_actions.SkipSagaAlwaysDoTheDefaultActionDemo(),
        override_actions.ReplaceContextWithYamlDumpDemo(),
        override_actions.OnActionComplete(),
        custom_models.UseOllamaDemo(),
        custom_models.UseAnthropic(),
        simulation_commands.SetStartTimeDemo(),
        simulation_commands.SimulationTickDemo(),
        simulation_commands.SelectSimObject(),
        character_commands.EnableAgentDemo(),
        character_commands.UpdateCharacterPropertyDemo(),
        character_commands.ChangeCharacterMemoriesDemo(),
        character_commands.OverrideCharacterAction(),
        character_commands.RobBankAndArrestCriminal(),
        character_commands.CustomConversation(),
        character_commands.FocusCharacter(),
        character_commands.PlaceCharacter(),
        camera_commands.FollowCharacter(),
        camera_commands.PlaceCamera(),
    ]

    while True:
        # Print the available demos and prompt the user to select one.
        print("\n -= Available Demos =- ")
        last_category = None
        for i, item in enumerate(options):
            if item.category != last_category:
                print(f"\n -= {item.category} =-")
                last_category = item.category
            print(f"> {i}: {item.name} - {item.description}")
        while True:
            try:
                print()
                value = input("Pick a demo to run: ")
                # Set the default to 0 if the user does not enter anything.
                if value == "":
                    pick = 0
                else:
                    pick = int(value)
                if pick >= len(options) or pick < 0:
                    print(
                        "Invalid input. Please enter a number between 0 and",
                        len(options),
                    )
                    continue
                break
            except ValueError:
                print("Invalid input. Please enter a number.")

        # Set the actions endpoint to the selected demo.
        item = options[pick]

        print("=" * 80)
        print(f"DEMO: {item.name}")
        print(f"CATEGORY: {item.category}")
        print(f"SUMMARY: {item.description}")
        # Allow for a much more detailed description of the demo to be printed.
        if item.function.__doc__:
            print(
                f"DETAILS: {item.function.__doc__}\n"
                f"DISCORD: https://blog.fabledev.com/blog/discord-community-now-open\n"
                f"WIKI: https://github.com/fablestudio/thistle-gulch/wiki"
            )
        print("=" * 80)
        continue_demo = input("Run this demo? [Y/n]: ")
        if continue_demo.lower() not in ["y", "yes", ""]:
            continue

        print(f"Setting Up Demo...")
        item.function(bridge)
        print(f"Running Demo...")

        try:
            bridge.run()
        except Exception as e:
            # Close the runtime if exception occurs.
            if bridge.runtime:
                bridge.runtime.terminate()
            raise e


if __name__ == "__main__":

    try:
        # Setup logging
        logging.basicConfig(
            level=logging.WARNING,
            stream=sys.stdout,
            format="<%(levelname)s> %(asctime)s - %(name)s - %(pathname)s:%(lineno)d\n    %(message)s",
        )
        thistle_gulch.logger.setLevel(logging.INFO)
        # This shows the generation of the response as it comes in.
        fable_saga.streaming_debug_logger.setLevel(logging.DEBUG)

        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Exiting...")
        input("Press Enter to exit.")
        sys.exit(1)
