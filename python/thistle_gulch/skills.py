from attrs import define
from typing import List
from fable_saga.actions import Action


@define(slots=True)
class GoToSkill:
    """
    Go to a location in the world
    """

    # The guid of the persona, item, or location to go to
    destination: str
    # Goal of the go to
    goal: str

    def to_action(self) -> Action:
        return Action(
            skill="go_to",
            parameters={"destination": self.destination, "goal": self.goal},
        )


@define(slots=True)
class ConverseWithSkill:
    """
    Walk to another character and talk to them
    """

    # The guid of the persona to converse with
    persona_guid: str
    # Optional pre-defined conversation to use. If no conversation is provided, one will be generated instead
    conversation: List[dict]
    # The topic of the conversation
    topic: str
    # Lots of helpful details to aid in conversation generation. Only used if no conversation is provided.
    context: str
    # Goal of the conversation
    goal: str

    def to_action(self) -> Action:
        return Action(
            skill="converse_with",
            parameters={
                "persona_guid": self.persona_guid,
                "conversation": self.conversation,
                "topic": self.topic,
                "context": self.context,
                "goal": self.goal,
            },
        )


@define(slots=True)
class ReflectSkill:
    """
    Think about things in order to synthesize new ideas and specific plans
    """

    # The topic of the reflection
    focus: str
    # The result of the reflection, e.g. a new plan or understanding you will remember
    result: str
    # Goal of the reflection
    goal: str

    def to_action(self) -> Action:
        return Action(
            skill="reflect",
            parameters={"focus": self.focus, "result": self.result, "goal": self.goal},
        )


@define(slots=True)
class WaitSkill:
    """
    Wait for a period of time while observing the world
    """

    # Number of minutes to wait
    duration: int
    # Goal of the wait
    goal: str

    def to_action(self) -> Action:
        return Action(
            skill="wait", parameters={"duration": self.duration, "goal": self.goal}
        )


@define(slots=True)
class InteractSkill:
    """
    Interact with an object or person in the world. See PersonaContextObject.interactables for available interactions
    """

    # The guid of the persona or item to interact with
    guid: str
    # The name of the interaction to use
    interaction: str
    # Goal of the interaction
    goal: str

    def to_action(self) -> Action:
        return Action(
            skill="interact",
            parameters={
                "item_guid": self.guid,
                "interaction": self.interaction,
                "goal": self.goal,
            },
        )


@define(slots=True)
class TakeToSkill:
    """
    Take an item or person to a location in the world
    """

    # The guid of the persona or item to take
    guid: str
    # The guid of the persona, item, or location where the item will be taken
    destination: str
    # Goal of the take to
    goal: str

    def to_action(self) -> Action:
        return Action(
            skill="take_to",
            parameters={
                "guid": self.guid,
                "destination": self.destination,
                "goal": self.goal,
            },
        )


@define(slots=True)
class ExchangeSkill:
    """
    Exchange resources with another entity's inventory.
    Creates new inventory items as needed on the fly.
    Use WorldContextObject.inventories to see a list of all available items
    """

    # The inventory item guid to give
    give_guid: str
    # Amount to give. Must be greater than 0
    give_amount: int
    # The inventory item guid to receive
    receive_guid: str
    # Amount to receive. Must be greater than 0
    receive_amount: int
    # (optional) The persona guid to exchange resources with. If not specified, the closest counterparty will be used
    counterparty_guid: str
    # Goal of the exchange
    goal: str

    def to_action(self) -> Action:
        return Action(
            skill="take_to",
            parameters={
                "give_guid": self.give_guid,
                "give_amount": self.give_amount,
                "receive_guid": self.receive_guid,
                "receive_amount": self.receive_amount,
                "counterparty_guid": self.counterparty_guid,
                "goal": self.goal,
            },
        )
