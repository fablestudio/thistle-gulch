import asyncio
import datetime

from fable_saga.actions import Action

from . import Demo, RuntimeBridge, formatted_input


class DefaultTutorial(Demo):
    def __init__(self):
        super().__init__(
            name="[Default] Thistle Gulch Tutorial",
            summary="A step-by-step tutorial of the Thistle Gulch simulation using the default SAGA server behavior.",
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

        intro_step = formatted_input(
            "Enter the step to start at (default is 1): ", "1", int
        )
        # intro_step is always incremented at the end the beginning of the tick function, so we need to decrement it.
        intro_step -= 1

        start_time: datetime.datetime

        async def on_ready(bridge: RuntimeBridge) -> bool:
            nonlocal start_time

            # First, we focus on a character to see their details.
            await bridge.runtime.api.focus_character("jack_kane")

            # Then we move the camera to follow them.
            await bridge.runtime.api.follow_character("jack_kane", 0.8)

            # Disable all agents that may have been enabled by the runtime args.
            # This way we can control the flow of the demo.
            context = await bridge.runtime.api.get_world_context()
            for persona in context.personas:
                await bridge.runtime.api.enable_agent(persona.persona_guid, False)

            # Create a future that can be awaited until the response is received.
            future = asyncio.get_event_loop().create_future()
            await bridge.runtime.api.modal(
                "Welcome to the Default Tutorial!",
                "This brief tutorial will guide you through how things work in the Thistle Gulch simulation. "
                "It's a work in progress and only covers the basics for now, but it should give you a good idea "
                "of how things work.\n\n"
                "For more information, check out the "
                '<link="https://www.youtube.com/playlist?list=PLmNhDGGwWOpo4NmTk4Yp1lIPL_NqTND__"><u>Youtube Playlist</u></link>, '
                '<link="https://github.com/fablestudio/thistle-gulch/wiki"><u>GitHub WIKI Documentation</u></link> or '
                '<link="https://blog.fabledev.com"><u>https://blog.fabledev.com</u></link>, as well as the various '
                "other demos which show how to extend and control the simulation via python code.",
                ["Start Tutorial"],
                False,
                future=future,
            )
            # Wait for the user to click the continue button.
            await future

            # Start the simulation (api.resume() is called automatically returning True).
            context = await bridge.runtime.api.get_world_context()
            start_time = datetime.datetime.fromisoformat(context.time)
            return True

        bridge.on_ready = on_ready

        pause_tick_handling = False

        async def on_tick(bridge: RuntimeBridge, current_time: datetime.datetime):
            nonlocal intro_step, start_time, pause_tick_handling
            if pause_tick_handling:
                return
            intro_step += 1
            pause_tick_handling = True

            if intro_step == 1:
                if current_time - start_time > datetime.timedelta(minutes=3):
                    # Create a future that can be awaited until the response is received.
                    future = asyncio.get_event_loop().create_future()
                    await bridge.runtime.api.modal(
                        f"[{intro_step}] Meet Blackjack Kane",
                        "The Saloon Owner and leader of the local criminal gang. To start with, he will force him to reflect on his current situation.",
                        ["Next"],
                        False,
                        future=future,
                    )
                    await future

            elif intro_step == 2:
                # Create a future that can be awaited until the response is received.
                future = asyncio.get_event_loop().create_future()
                await bridge.runtime.api.override_character_action(
                    "jack_kane",
                    Action(
                        "reflect",
                        {
                            "focus": "The current situation in Thistle Gulch.",
                            "result": "Bring the audience up to speed on who blackjack is and the context of the story.",
                            "goal": "Bring the audience up to speed on who blackjack is and the context of the story.",
                        },
                    ),
                    future=future,
                )
                await future

            elif intro_step == 3:
                # Create a future that can be awaited until the response is received.
                future = asyncio.get_event_loop().create_future()
                await bridge.runtime.api.modal(
                    f"[{intro_step}] Generating Conversations",
                    "The REFLECT action generates a self-conversation for blackjack. We didn't tell it exactly what to say,"
                    " but it should have used blackjack's recent memories and the story context to summarize things.\n\n"
                    "The conversation is generated via the 'Bridge' which is the python code this demo is running from. "
                    "This environment you see in front of you is the 'Runtime' which is the simulation environment.\n\n"
                    "Your code can drive the simulation by sending commands to the runtime, but that isn't the only way..",
                    ["Next"],
                    False,
                    future=future,
                )
                await future

            elif intro_step == 4:
                # Create a future that can be awaited until the response is received.
                future = asyncio.get_event_loop().create_future()
                await bridge.runtime.api.modal(
                    f"[{intro_step}] Generating Actions via SAGA",
                    "By default, the characters use a Utility AI to drive their actions, which runs instantly within "
                    "the runtime and doesn't incur any LLM costs. Characters can have have their SAGA Agent enabled to "
                    "generate multiple actions and score them using the Bridge. This takes time and incurs LLM costs.\n\n"
                    "Similar to the conversation generation, actions are generated by the 'Bridge' and then sent to the "
                    "'Runtime'",
                    ["Next"],
                    False,
                    future=future,
                )
                await future

            elif intro_step == 5:
                # Create a future that can be awaited until the response is received.
                future = asyncio.get_event_loop().create_future()
                await bridge.runtime.api.modal(
                    f"[{intro_step}] Choosing Actions via SAGA",
                    "Action Generation with SAGA is actually a list of actions instead of just one, along with scores "
                    "for each from -1 to +1. The Runtime either chooses the best action automatically, or the user can "
                    "choose one manually via a modal that appears in the Runtime, which is the default behavior.\n\n"
                    "The list of actions is in score order, so the first action is the best one. But the user can choose "
                    "any action they want or event choose 'cancel' to do the default action (via the Utility AI).\n\n"
                    "Let's activate the SAGA Agent for Blackjack Kane and see what actions it generates.",
                    ["Enable SAGA Agent for Blackjack Kane"],
                    False,
                    future=future,
                )
                await future

                # Activate the SAGA agent for Blackjack Kane so when the wait action is done, it will generate a list of actions.
                await bridge.runtime.api.enable_agent("jack_kane", True)

                # TODO: Basically this is a hack to Cancel the current action which will trigger generating the list.
                future = asyncio.get_event_loop().create_future()
                await bridge.runtime.api.override_character_action(
                    "jack_kane",
                    Action("wait", {"duration": 1}),
                    future=future,
                )
                await future
                # We have to increment so that the on_action_complete step is triggered while we pause the tick handling.
                intro_step += 1
                return  # Keep pause_tick_handling until the wait action is done.

            elif intro_step == 7:
                # Create a future that can be awaited until the response is received.
                future = asyncio.get_event_loop().create_future()
                await bridge.runtime.api.modal(
                    f"[{intro_step}] Keep Exploring",
                    "To learn more about the runtime controls and how to interact with the simulation outside of code, "
                    "checkout the <link=https://github.com/fablestudio/thistle-gulch/wiki/Runtime><u>WIKI Runtime Documentation.</u></link> "
                    "We hope you enjoy using the Thistle Gulch platform!\n\n"
                    "Do you want to keep blackjack (jake_kane) enabled with the SAGA agent?",
                    ["Yes", "No"],
                    True,
                    future=future,
                )
                modal_response = await future
                choice_idx = modal_response["choice"]
                if choice_idx != 0:
                    await bridge.runtime.api.enable_agent("jack_kane", False)
                    await bridge.runtime.api.modal(
                        "SAGA Agent Disabled",
                        "The SAGA agent has been disabled for Blackjack Kane. You can enable it again at any time.",
                        ["Ok"],
                        False,
                    )
                return  # End the demo (continue to pause the tick handling).
            pause_tick_handling = False

        bridge.on_tick = on_tick

        async def on_action_complete(
            bridge: RuntimeBridge, persona_id: str, completed_action: str
        ):
            nonlocal intro_step
            nonlocal pause_tick_handling
            if persona_id == "jack_kane" and intro_step == 6:
                # The option the user selected should now be completed.

                # Create a future that can be awaited until the response is received.
                future = asyncio.get_event_loop().create_future()
                await bridge.runtime.api.modal(
                    f"[Step {intro_step}] Action Complete",
                    f"It looks like you selected {completed_action} for Blackjack Kane. That action is now complete. "
                    "The SAGA agent will generate a new list of actions for you to choose from.",
                    ["Next"],
                    True,
                    future=future,
                )
                await future
                # Note we don't increment the intro_step because it will be incremented in the on_tick function.
                pause_tick_handling = False

        bridge.on_action_complete = on_action_complete
