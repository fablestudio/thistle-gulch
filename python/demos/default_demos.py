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
        start_time: datetime.datetime

        async def on_ready(bridge: RuntimeBridge) -> bool:
            nonlocal start_time

            # First, we focus on a character to see their details.
            await bridge.runtime.api.focus_character("jack_kane")

            # Then we move the camera to follow them.
            await bridge.runtime.api.follow_character("jack_kane", 0.8)

            future = await bridge.runtime.api.modal(
                "Welcome to the default SAGA server demo!",
                "This is the default behavior of the bridge. The SAGA server is generating actions and conversations for the agents in the simulation.",
                ["Continue"],
                False,
            )
            # Wait for the user to click the continue button.
            await future

            # Start the simulation (api.resume() is called automatically returning True).
            context = await bridge.runtime.api.get_world_context()
            start_time = datetime.datetime.fromisoformat(context.time)
            return True

        bridge.on_ready = on_ready

        processing = False

        async def on_tick(bridge: RuntimeBridge, current_time: datetime.datetime):
            nonlocal intro_step, start_time, processing
            if processing:
                return

            if intro_step == 0:
                if current_time - start_time > datetime.timedelta(minutes=3):
                    processing = True
                    future = await bridge.runtime.api.modal(
                        "Demo Complete",
                        "The default SAGA server demo is complete.",
                        ["Close"],
                        False,
                    )
                    await future
                    intro_step += 1
                    processing = False

        bridge.on_tick = on_tick
