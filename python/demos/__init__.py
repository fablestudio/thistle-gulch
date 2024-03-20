from typing import Callable

from thistle_gulch.bridge import RuntimeBridge


class Demo:
    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        function: Callable[[RuntimeBridge], None],
    ):
        self.name = name
        self.description = description
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
            description="Just run the default SAGA server, which is the default behavior of the bridge.",
            function=lambda bridge: None,
        )
