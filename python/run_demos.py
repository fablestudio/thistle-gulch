import logging
import sys

import thistle_gulch.bridge as tg_bridge
import demos.override_action_options as action_overrides


def main():

    # A list of available demos and the corresponding endpoint they override.
    options = [
        (action_overrides.PrintActionsAndPickFirst, "actions_endpoint"),
        (action_overrides.SkipSagaAlwaysDoTheDefaultAction, "actions_endpoint"),
        (action_overrides.ReplaceContextWithYamlDump, "actions_endpoint"),
        (action_overrides.UseLlama2Model, "actions_endpoint")
    ]

    # Print the available demos and prompt the user to select one.
    print ("\n -= Available Demos =- ")
    for i, item in enumerate(options):
        print(f"{i}: {item[0].__name__}")
    while True:
        try:
            pick = int(input("Pick a demo to run: "))
            if pick >= len(options) or pick < 0:
                print("Invalid input. Please enter a number between 0 and", len(options))
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Set the actions endpoint to the selected demo.
    item = options[pick]
    if item[1] == "actions_endpoint":
        tg_bridge.BridgeConfig.actions_endpoint = item[0]()

    # Run the bridge.
    tg_bridge.main()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='<%(levelname)s> %(asctime)s - %(name)s - %(pathname)s:%(lineno)d\n    %(message)s')
    main()
