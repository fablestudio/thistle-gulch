from typing import Callable, Awaitable

from thistle_gulch.bridge import RuntimeBridge


class Demo:
    def __init__(self, name: str, description: str, function: Callable[[RuntimeBridge], None]):
        self.name = name
        # self.description = description
        self.function = function

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

