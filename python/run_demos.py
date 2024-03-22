import logging
import sys
from typing import List

import demos.override_action_options as action_overrides
import demos.simulation_commands as simulation_commands
import thistle_gulch.bridge as tg_bridge
from demos import Demo, DefaultSagaServerDemo


def main():
    # Run the bridge.
    bridge = tg_bridge.main(auto_run=False)

    # A list of available demos and the corresponding endpoint they override.
    options: List[Demo] = [
        DefaultSagaServerDemo(),
        action_overrides.PrintActionsAndPickFirstDemo(),
        action_overrides.SkipSagaAlwaysDoTheDefaultActionDemo(),
        action_overrides.ReplaceContextWithYamlDumpDemo(),
        action_overrides.UseLlama2ModelDemo(),
        simulation_commands.SetStartTimeDemo(),
    ]

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
            pick = int(input("Pick a demo to run: "))
            if pick >= len(options) or pick < 0:
                print(
                    "Invalid input. Please enter a number between 0 and", len(options)
                )
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Set the actions endpoint to the selected demo.
    item = options[pick]
    item.function(bridge)
    #
    # elif item[1] == "actions_endpoint":
    #     tg_bridge.BridgeConfig.actions_endpoint = item[0]()
    bridge.run()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="<%(levelname)s> %(asctime)s - %(name)s - %(pathname)s:%(lineno)d\n    %(message)s",
    )
    main()
