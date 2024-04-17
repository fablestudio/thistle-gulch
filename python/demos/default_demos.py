import datetime

from . import Demo, RuntimeBridge


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

        intro_step = 0

        async def on_ready(bridge: RuntimeBridge) -> bool:

            # First, we focus on a character to see their details.
            await bridge.runtime.api.focus_character("jack_kane")

            # Then we move the camera to follow them.
            await bridge.runtime.api.follow_character("jack_kane", 0.8)

            await bridge.runtime.api.modal(
                "Welcome to the default SAGA server demo!",
                "This is the default behavior of the bridge. The SAGA server is generating actions and conversations for the agents in the simulation.",
                ["Continue"],
            )

            # pause the simulation to allow the user to see everything.
            return False

        bridge.on_ready = on_ready
        start_time: datetime.datetime

        async def on_tick(bridge: RuntimeBridge, current_time: datetime.datetime):
            nonlocal intro_step, start_time
            if intro_step == 1:
                print("Step two - save the start_time")
                start_time = current_time
                intro_step += 1
            elif intro_step == 2:
                if current_time - start_time > datetime.timedelta(seconds=10):
                    await bridge.runtime.api.modal(
                        "Demo Complete",
                        "The default SAGA server demo is complete.",
                        ["Close"],
                    )
                    intro_step += 1

        bridge.on_tick = on_tick

        async def on_event(bridge: RuntimeBridge, name: str, data: dict):
            nonlocal intro_step
            if intro_step == 0:
                print("Step one, resume the simulation.")
                await bridge.runtime.api.resume()
                intro_step += 1

        bridge.on_event = on_event
