import logging
import sys
from typing import List

import thistle_gulch
import thistle_gulch.bridge as tg_bridge
from demos import Demo, DefaultSagaServerDemo, override_action_options, simulation_commands, character_commands


def main():
    # Run the bridge.
    bridge = tg_bridge.main(auto_run=False)

    # A list of available demos and the corresponding endpoint they override.
    options: List[Demo] = [
        DefaultSagaServerDemo(),
        override_action_options.PrintActionsAndPickFirstDemo(),
        override_action_options.SkipSagaAlwaysDoTheDefaultActionDemo(),
        override_action_options.ReplaceContextWithYamlDumpDemo(),
        override_action_options.UseLlama2ModelDemo(),
        simulation_commands.SetStartTimeDemo(),
        simulation_commands.SimulationTickDemo(),
        character_commands.EnableAgentDemo(),
        character_commands.UpdateCharacterPropertyDemo(),
        character_commands.OverrideCharacterAction(),
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
        level=logging.WARNING,
        stream=sys.stdout,
        format="<%(levelname)s> %(asctime)s - %(name)s - %(pathname)s:%(lineno)d\n    %(message)s",
    )
    thistle_gulch.logger.setLevel(logging.INFO)

    main()
