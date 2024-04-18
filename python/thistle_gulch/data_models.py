import datetime
from typing import Optional, List, Dict
from attrs import define
from fable_saga.actions import Skill


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
    item_guid: str
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
