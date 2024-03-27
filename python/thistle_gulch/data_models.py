import datetime
from typing import Optional, List, Dict

from attrs import define


@define(slots=True)
class Persona:
    persona_guid: str
    name: str
    summary: str
    description: str = ""
    backstory: str = ""
    energy_level: str = ""


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
    time_ago: str
    summary: str


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
    item_guid: str
    name: str
    description: str
    interactions: List[str]


@define(slots=True)
class PersonaContextObject:
    time: str
    participants: List[str]
    personas: List[Persona]
    observations: List[Observation]
    inventories: List[Inventory]
    conversations: List[Conversation]
    interactables: List[Interactable]
    locations: List[Location]
    memories: List[PersonaMemories]
    default_action: str
