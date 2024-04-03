from typing import Callable

from thistle_gulch.bridge import RuntimeBridge


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
