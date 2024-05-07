import datetime
from typing import Optional, List, Dict
from attrs import define
from fable_saga.actions import Skill


@define(slots=True)
class Vector3:
    x: float
    y: float
    z: float

    @staticmethod
    def distance(v1, v2):
        return ((v1.x - v2.x) ** 2 + (v1.y - v2.y) ** 2 + (v1.z - v2.z) ** 2) ** 0.5


@define(slots=True)
class Persona:
    persona_guid: str = ""
    name: str = ""
    summary: str = ""
    description: str = ""
    backstory: str = ""
    energy_level: str = ""
    position: Optional[Vector3] = None
    location_id: str = ""
    destination_id: str = ""
    actions_enabled: Optional[bool] = None
    conversations_enabled: Optional[bool] = None


@define(slots=True)
class SimObject:
    guid: str
    name: str
    description: str
    position: Vector3
    location_id: str


@define(slots=True)
class Location:
    guid: str
    name: str
    description: str
    parent_guid: str
    center: Vector3
    extents: Vector3
    center_floor_position: Vector3


@define(slots=True)
class ConversationTurn:
    persona_guid: str
    dialogue: str


@define(slots=True)
class Conversation:
    timestamp: str
    transcript: List[ConversationTurn]


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
class Memory:
    guid: str
    timestamp: str
    summary: str
    context_id: str
    entity_ids: List[str]
    position: Vector3
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
    sim_objects: List[SimObject]


@define(slots=True)
class PersonaContextObject:
    time: str
    participants: List[str]
    observations: List[Observation]
    interactables: List[Interactable]
    current_action: str
    default_action: str
    world_context: WorldContextObject
