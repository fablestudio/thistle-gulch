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

            await bridge.runtime.api.modal("Welcome to the default SAGA server demo!", "This is the default behavior of the bridge. The SAGA server is generating actions and conversations for the agents in the simulation.", "Continue")

            # pause the simulation to allow the user to see everything.
            return False
        bridge.on_ready = on_ready

        async def on_tick(bridge: RuntimeBridge, current_time: datetime.datetime):
            nonlocal intro_step
            if intro_step == 0:
                print("Welcome to the SAGA server! This is the default behavior.")
                print("We will focus on Jack Kane and follow him with the camera.")
                intro_step += 1

        bridge.on_tick = on_tick

