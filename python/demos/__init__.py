import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional, List, Any, Dict

from thistle_gulch.bridge import RuntimeBridge
from thistle_gulch.data_models import WorldContextObject


async def choose_from_list(
    text: str, options: List[str] | Dict[str, str], exclude: Optional[List[str]] = None
) -> str:
    """
    Helper for choosing one option from a list of options.
    :rtype: object
    :param options: The list of string options to choose from.
    :param text: The text to display to the user.
    :param exclude: A list of options to exclude from the list.
    :return:
    """
    options_list = options.copy()
    if isinstance(options, dict):
        options_list = list(options.keys())

    if exclude:
        options_list = [c for c in options_list if c not in exclude]

    def validator(choice: str) -> str:
        if choice == "":
            if isinstance(options, list):
                print(options_list)
            if isinstance(options, dict):
                for key in options_list:
                    print(f"* [{key}]: {options[key]}")
            raise ValueError("You must pick from this list..")
        if choice in options_list:
            return choice
        raise ValueError(f"Invalid choice: {choice}")

    input_text = text + " [Enter for list]"
    return await formatted_input_async(input_text, validator=validator)


def formatted_input(
    prompt: str,
    default: Optional[str] = None,
    validator: Optional[Callable[[str], Any]] = None,
) -> Any:
    """
    Get input from the user, with a default value.
    :param prompt: The prompt to display to the user.
    :param default: The default value to use if the user does not enter anything. It is still validated.
    :param validator: A function that takes the user's input and returns the validated input.
        Raises an exception if the input is invalid. Note return value is the new input and may not be a string.
    :return: The user's input, or the default value if the user did not enter anything.
    """
    prefix = "\n->"
    while True:
        user_input = input(f"{prefix} {prompt}: ")
        # If the user just pressed enter, and there is a default value, use the default value.
        # The default value is still validated, so it needs to start as a string, and then the
        # validator can convert it to the correct type.
        if user_input == "" and default:
            user_input = default
            print(f"\tUsing default value of {default}")
        # If a validator is provided, use it to validate the input and consider its result the new input.
        if validator:
            try:
                user_input = validator(user_input)
                return user_input
            # If the validator raises an exception, print the exception and prompt again.
            except Exception as e:
                print(f"{prefix} {e}")
                continue
        break
    return user_input


async def formatted_input_async(
    prompt: str,
    default: Optional[str] = None,
    validator: Optional[Callable[[str], Any]] = None,
) -> Any:
    with ThreadPoolExecutor(1, "AsyncInput") as executor:
        return await asyncio.get_event_loop().run_in_executor(
            executor, formatted_input, prompt, default, validator
        )


def yes_no_validator(val: str) -> int:
    val = val.lower()
    if val == "y" or val == "yes":
        return 1
    if val == "n" or val == "no":
        return 0
    raise ValueError("Please enter 'y' or 'n'.")


async def disable_all_agents(
    bridge: RuntimeBridge, world_context: Optional[WorldContextObject] = None
):
    """Disable all agents' actions and conversations"""
    if world_context is None:
        world_context = await bridge.runtime.api.get_world_context()
    for persona in world_context.personas:
        await bridge.runtime.api.enable_agent(persona.persona_guid, False, False)


class Demo:
    def __init__(
        self,
        name: str,
        summary: str,
        category: str,
        function: Callable[[RuntimeBridge], None],
    ):
        self.name = name
        self.description = summary
        self.category = category
        self.function = function

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
