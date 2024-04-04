import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional, List, Any, Dict

from thistle_gulch.bridge import RuntimeBridge


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


async def get_persona_list(bridge) -> Dict[str, str]:
    # Get the character context for jack_kane, just to get the list of persona ids.
    context = await bridge.runtime.api.get_character_context("jack_kane")
    return dict(
        [(persona.persona_guid, persona.summary) for persona in context.personas]
    )


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
        # If a validator is provided, use it to validate the input and consider its result the new input.
        if validator:
            try:
                # If the validator raises an exception, print the exception and prompt again.
                user_input = validator(user_input)
                return user_input
            except Exception as e:
                print(f"{prefix} {e}")
                continue
        else:
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


class DefaultSagaServerDemo(Demo):
    def __init__(self):
        super().__init__(
            name="[Default] Saga Server",
            summary="Just run the default SAGA server, which is the default behavior of the bridge.",
            function=self.run_default,
            category="Default",
        )

    def run_default(self, bridge: RuntimeBridge):
        """Use the fable_saga.server library to generate actions and conversations. (Default behavior)

        SAGA stands for (Skill To Action Generation) for more information on how SAGA works, check out the blog post:
        https://blog.fabledev.com/blog/announcing-saga-skill-to-action-generation-for-agents-open-source

        The library also does conversation generation as an added bonus, so we leverage that as well.
        If you wanted to override either of these behaviors, you would need to override the corresponding endpoints,
        which is what many of the other demos in this list do.
        """
        # No need to do anything here, the default behavior is to run the SAGA server.
        pass
