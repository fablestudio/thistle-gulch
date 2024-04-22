import datetime
from typing import Optional, List, Dict
from attrs import define
from fable_saga.actions import Skill, Action


@define(slots=True)
class Persona:
    persona_guid: str
    name: str
    summary: str
    description: str = ""
    backstory: str = ""
    energy_level: str = ""
    position: List[float] = [0] * 3
    location_id: str = ""
    destination_id: str = ""


@define(slots=True)
class SimObject:
    guid: str
    display_name: str
    description: str

    @staticmethod
    def from_dict(obj):
        params = {
            "guid": obj["id"],
            "display_name": obj["displayName"],
            "description": obj["description"],
        }
        return SimObject(**params)


# @define(slots=True)
# class Location:
#     guid: str
#     name: str
#     description: str
#     parent_guid: str
#     center: "Vector3"
#     extents: "Vector3"
#     center_floor_position: "Vector3"


@define(slots=True)
class StatusUpdate:
    timestamp: datetime.datetime
    guid: str
    sequence: str
    sequence_step: str
    position: "Vector3"
    location_id: str
    destination_id: str


@define(slots=True)
class SequenceStep:
    timestamp: datetime.datetime
    guid: str
    sequence: str
    starting_step: str
    completed_step: str
    completed_step_duration: float
    interrupted: bool


@define(slots=True)
class Conversation:
    time_ago: str
    transcript: List[Dict[str, str]]


@define(slots=True)
class Vector3:
    x: float
    y: float
    z: float

    @staticmethod
    def distance(v1, v2):
        return ((v1.x - v2.x) ** 2 + (v1.y - v2.y) ** 2 + (v1.z - v2.z) ** 2) ** 0.5


@define(slots=True)
class Observation:
    persona_guid: str
    action: str
    action_step: str
    distance: str


@define(slots=True)
class SequenceUpdate:
    timestamp: datetime.datetime
    persona_guid: str
    action: str
    action_step_started: Optional[str]
    action_step_completed: Optional[str]
    interrupted: bool


@define(slots=True)
class Location:
    name: str
    description: str


@define(slots=True)
class Memory:
    guid: str
    timestamp: str
    summary: str
    context_id: str
    entity_ids: List[str]
    position: List[float]
    importance_weight: float


@define(slots=True)
class PersonaMemories:
    persona_guid: str
    memories: List[Memory]


@define(slots=True)
class Inventory:
    owner_guid: str
    resources: List[str]


@define(slots=True)
class Interactable:
    guid: str
    name: str
    description: str
    interactions: List[str]


@define(slots=True)
class WorldContextObject:
    time: str
    time_formatted: str
    skills: List[Skill]
    personas: List[Persona]
    inventories: List[Inventory]
    conversations: List[Conversation]
    locations: List[Location]
    memories: List[PersonaMemories]


@define(slots=True)
class PersonaContextObject:
    time: str
    participants: List[str]
    observations: List[Observation]
    interactables: List[Interactable]
    current_action: str
    default_action: str
    world_context: WorldContextObject


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
