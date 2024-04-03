import logging
import sys
from typing import List

import demos.custom_models as custom_models
import thistle_gulch
import thistle_gulch.bridge as tg_bridge
from demos import (
    Demo,
    DefaultSagaServerDemo,
    override_actions,
    simulation_commands,
    character_commands,
)


def main():
    # Run the bridge.
    bridge = tg_bridge.main(auto_run=False)

    # A list of available demos and the corresponding endpoint they override.
    options: List[Demo] = [
        DefaultSagaServerDemo(),
        override_actions.PrintActionsAndPickFirstDemo(),
        override_actions.SkipSagaAlwaysDoTheDefaultActionDemo(),
        override_actions.ReplaceContextWithYamlDumpDemo(),
        custom_models.UseOllamaDemo(),
        simulation_commands.SetStartTimeDemo(),
        simulation_commands.SimulationTickDemo(),
        character_commands.EnableAgentDemo(),
        character_commands.UpdateCharacterPropertyDemo(),
        character_commands.OverrideCharacterAction(),
        character_commands.RobBankAndArrestCriminal(),
        character_commands.CustomConversation(),
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
            print(f"DETAILS: {item.function.__doc__}")
        print("=" * 80)
        continue_demo = input("Run this demo? [Y/n]: ")
        if continue_demo.lower() not in ["y", "yes", ""]:
            continue

        print(f"Setting Up Demo...")
        item.function(bridge)
        print(f"Running Demo...")

        bridge.run()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stdout,
        format="<%(levelname)s> %(asctime)s - %(name)s - %(pathname)s:%(lineno)d\n    %(message)s",
    )
    thistle_gulch.logger.setLevel(logging.INFO)

    main()
