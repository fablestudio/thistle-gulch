import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
from enum import Enum

import cattrs
from langchain_core.messages import AIMessage
import fable_saga.server

import thistle_gulch.bridge
from thistle_gulch.bridge import RuntimeBridge
from thistle_gulch.data_models import ModelConfig, WorldContextObject
from thistle_gulch.skills import GoToSkill, ConverseWithSkill, ReflectSkill, Action, WaitSkill

# Change the guidance to a Christmas Carol.
guidance = \
    """
    It's Christmas Eve in Thistle Gulch. The town is depressed and the people are poor, but Reverend Blackwood wants to
    change that. He's planning a Christmas Carol for the town, but he needs to gather some people to help him.
    He's looking for a few good people to help him spread some Christmas cheer, or so he says.
    Sarah Brown has wearily agreed to help by convincing others in town to join the Carol. She's not sure if it will work,
    given the town's mood, but she's willing to try.
    
    Each character (blackwood or brown) has a different set of skills that they can use. First the two characters will
    discuss who to recruit and which one of them will do the recruiting. Then they will go out and try to recruit the
    people they've decided on. They will use their skills to try to convince the people to join the Carol. Each person they
    try to convince will state whether they will join or not. If they join, they will return to their normal activities
    until the Carol starts at 6pm. They will not offer to recruit anyone else. Characters can and should refuse to join
    the Carol if they are busy or if it's out of character.
    
    At 6pm, the Carol will start. The goal is to have as many people as possible join the Carol. The more people that join,
    the more successful the Carol will be. The Carol will last for 1 hour, and then the story will end.
    
    """


class CustomConversationEndpoint(thistle_gulch.bridge.TGConversationEndpoint):

    # TODO: This is a little clunky, but it works for now. We need to override the handle_request method to replace the
    #  murder guidance with the Christmas Carol guidance.
    async def handle_request(self, request: thistle_gulch.bridge.TGConversationRequest):
        request.context = guidance + "\nTASK:\n" + request.context.split("\nTask:")[1]
        request.model = None
        return await super().handle_request(request)


class CarolState(Enum):
    PRE_ORGANIZE = "pre_organize"
    ORGANIZE = "organize"
    WAITING = "waiting"
    GATHERING = "gathering"
    STARTING = "starting"
    STARTED = "started"
    STOPPING = "stopping"
    ENDING = "ending"
    ENDED = "ended"


class NPCState(Enum):
    READY = "ready"
    DECLINED = "declined"
    WAITING = "waiting"
    BUSY = "busy"
    SINGING = "singing"
    DONE = "done"


def main():
    bridge = thistle_gulch.bridge.main(auto_run=False)

    carol_time = datetime(1890, 12, 24, 18, 0, 0)
    organizers = ["sarah_brown", "ezekiel_blackwood"]
    participants: Dict[str, NPCState] = {name: NPCState.READY for name in organizers}

    carol_state = CarolState.PRE_ORGANIZE

    async def wait_action(npc: str, action: Action):
        future = asyncio.get_event_loop().create_future()
        participants[npc] = NPCState.BUSY
        await bridge.runtime.api.override_character_action(npc, action, future, wait=True)
        await future
        print(future.result())
        participants[npc] = NPCState.READY

    async def wait_modal(title: str, message: str, buttons: Optional[List[str]], pause: bool) -> None:
        future = asyncio.get_event_loop().create_future()
        await bridge.runtime.api.modal(title, message, buttons, pause, future)
        await future

    async def stay_put(persona_guid: str, goal: str):
        nonlocal participants
        wait = WaitSkill(goal=goal, duration=-1).to_action()
        participants[persona_guid] = NPCState.WAITING
        await bridge.runtime.api.override_character_action(persona_guid, wait, wait=True)

    async def as_you_were(persona_guid: str):
        nonlocal participants
        participants[persona_guid] = NPCState.READY
        await bridge.runtime.api.override_character_action(persona_guid, None)

    async def plan_and_recruit():
        nonlocal carol_state, organizers, participants
        # Make sure we don't generate any actions while recruiting.
        for organizer in organizers:
            participants[organizer] = NPCState.BUSY

        persona_id = organizers[0]
        if persona_id in organizers:
            print(persona_id)
            other_organizer = [org for org in organizers if org != persona_id][0]
            await wait_action(persona_id, ConverseWithSkill(
                persona_guid=other_organizer,
                topic="Recruiting Singers for the Christmas Carol this evening",
                context="Christmas Carol",
                goal="Pick a new person to recruit and which character will do the recruiting.",
                conversation=None,
            ).to_action())
            #TODO: Get the result of the conversation and define the next action.
            ctx = await bridge.runtime.api.get_world_context()
            convo = ctx.conversations[-1]
            prompt = "TRANSCRIPT:\n" + \
                json.dumps(cattrs.unstructure(convo.transcript)) + "\n" + \
                "PERSONAS:\n" + \
                "\n".join([p.persona_guid for p in ctx.personas]) + "\n" + \
                "TASK:\n" + \
                "Based on the transcript, convert what the characters decided to do into the following JSON format:" + \
                ' {"plans": [recruiter_id: <persona_guid>, "recruit_ids": [<persona_guid>]}'
            result: AIMessage = await llm.ainvoke(prompt)  # type: ignore
            print(result.content)
            if not isinstance(result.content, str):
                raise ValueError("Expected a string response from the model.")

            plan: List[Dict[str, Any]] = json.loads(result.content)["plans"]
            await asyncio.gather(*[go_recruit(item['recruiter_id'], item['recruit_ids']) for item in plan])

            # # Find the next person to recruit.
            # world_state = await bridge.runtime.api.get_world_context()
            # remaining_people = [p for p in world_state.personas if p.persona_guid not in participants]
            # if not remaining_people:
            #     # If there are no more people to recruit, go about your business.
            #     await as_you_were(other_organizer)
            #     await as_you_were(persona_id)
            #     carol_state = CarolState.WAITING
            #     return
            # else:
            #     # Set the other organizer to waiting while this organizer goes to find the next person.
            #     await stay_put(other_organizer, f"Waiting for {persona_id} to recruit the next person")
            #     await go_recruit(persona_id, remaining_people[0].persona_guid, other_organizer)

    async def go_recruit(recruiter: str, targets: List[str]):
        nonlocal participants
        #await stay_put(target, f"{recruiter} wants to talk to me.")
        #goto = GoToSkill(goal="Recruit a singer for the Christmas Carol", destination=target).to_action()
        #await wait_action(target, goto)

        future = asyncio.get_event_loop().create_future()

        for target in targets:
            conversation = ConverseWithSkill(
                persona_guid=target,
                topic="Recruiting Singers for the Christmas Carol",
                context="Christmas Carol",
                goal="Recruit Singers",
                conversation=None,
            ).to_action()
            await wait_action(recruiter, conversation)

            #TODO: Was the conversation successful? If so, set the target to ready.
            await as_you_were(target)

    # Create a custom conversation agent for the Christmas Carol - we will change the template later.
    llm = thistle_gulch.bridge.dynamic_model_loader(cattrs.structure(bridge.config.conversation_llm, ModelConfig))
    conversation_agent = thistle_gulch.bridge.ConversationAgent(llm=llm)

    # Create the override endpoints (we may not need both).
    override_conversations = thistle_gulch.bridge.Route(
        thistle_gulch.IncomingRoutes.generate_conversations.value,
        CustomConversationEndpoint(
            conversation_agent
        ),
    )
    # Override the conversation endpoint.
    bridge.router.add_route(override_conversations)

    async def on_ready(bridge: RuntimeBridge, world_context: WorldContextObject):
        nonlocal carol_time, carol_state, organizers, participants

        # Disable all agents except the organizers and even then, only enable the conversation agent for each.
        if world_context is None:
            world_context = await bridge.runtime.api.get_world_context()
        for persona in world_context.personas:
            await bridge.runtime.api.enable_agent(persona.persona_guid, False, persona.persona_guid in organizers)

        print("Setting the time to Christmas Eve Day.")
        await bridge.runtime.api.set_start_date(carol_time - timedelta(hours=5))
        print("Time set.")

        # TODO: Add memories for the characters of why they are doing this.

        organizer_npc = organizers[0]
        partner_npc = organizers[1]

        carol_state = CarolState.ORGANIZE
        participants[organizer_npc] = NPCState.BUSY
        participants[partner_npc] = NPCState.WAITING

        await wait_modal("The Christmas Carol", guidance, ["Start"], False)
        await bridge.runtime.api.resume()

        # initial_conversation = ConverseWithSkill(
        #     persona_guid=partner_npc,
        #     topic="Recruiting Singers for the Christmas Carol",
        #     context="Christmas Carol",
        #     goal="Recruit Singers",
        #     conversation=[
        #         {"persona_guid": organizer_npc, "dialogue": "We need to find some singers for the Christmas Carol."}],
        # )
        #
        # await wait_action(organizer_npc, initial_conversation.to_action())
        while carol_state == CarolState.ORGANIZE:
            await plan_and_recruit()

    # async def on_tick(_, current_time: datetime):
    #     nonlocal carol_time, carol_state, participants
    #     # Only trigger the arrest once at the designated time
    #     organizer_states = [participants[p] for p in participants if p in organizers]
    #
    #     if current_time >= carol_time and carol_state == CarolState.ORGANIZE:
    #         carol_state = CarolState.GATHERING
    #         #TODO: Gather everyone at the church.
    #
    #     # elif carol_state == CarolState.ORGANIZE and NPCState.READY in organizer_states:
    #     #     await plan_and_recruit()
    #     elif carol_state == CarolState.GATHERING:
    #         #TODO: Has everyone arrived at the church? If so, start the carol.
    #         pass






        # elif carol_state == CarolState.NOT_STARTED:
        #     await wait_modal("Gather up", "Gather round, the Christmas Carol is about to begin!")
        #     carol_state = "waiting"
        #     goto_church = GoToSkill(goal="Join the Christmas Carol", destination="church").to_action()
        #
        #     futures = []
        #     for person in participants:
        #         future = asyncio.Future()
        #         await bridge.runtime.api.override_character_action(person, goto_church, future)
        #         futures.append(future)
        #     await asyncio.gather(*futures)
        #
        # elif carol_state == "starting":
        #     carol_state = "started"
        #     await bridge.runtime.api.modal("Everyone has arrived", "The Christmas Carol has started!")
        #     line = "We wish you a merry Christmas!"
        #     wait_for = []
        #     for person in participants:
        #         # TODO: Looks like converse_with doesn't work with a single character in the Runtime.
        #         # Basically, it assumes a companion character, so we need to use ReflectSkill instead.
        #         # singing_convo = ConverseWithSkill(
        #         #     persona_guid=person,
        #         #     conversation=[{"persona_guid":person, "dialogue": line} for i in range(3)],
        #         #     topic="Singing",
        #         #     context="Christmas Carol",
        #         #     goal="Sing the Christmas Carol",
        #         # )
        #         singing = ReflectSkill(focus="Sing a Christmas Carol to yourself", result="3 lines of a christmas carol were sung", goal="Sing the Carol")
        #         future = asyncio.Future()
        #         await bridge.runtime.api.override_character_action(person, singing.to_action(), future)
        #         wait_for.append(future)
        #     await asyncio.gather(*wait_for)
        #     carol_state = "stopping"
        # elif carol_state == "ending":
        #     print("The Christmas Carol has ended!")
        #     await bridge.runtime.api.modal("The End", "The Christmas Carol has ended!", None)
        #     carol_state = "ended"

    # async def on_action_complete(bridge, persona_id, action) -> Optional[Action]:
    #     nonlocal carol_state, participants
    #
    #     if persona_id in participants and participants[persona_id] == NPCState.WAITING:
    #         wait = WaitSkill(goal="Better keep waiting", duration=-1).to_action()
    #         participants[persona_id] = NPCState.WAITING
    #         return wait
    #
    #     if persona_id in participants and participants[persona_id] == NPCState.BUSY:
    #         #logger.error(f"Person {persona_id} is busy, but the action is complete.")
    #         wait = WaitSkill(goal="Better keep waiting", duration=-1).to_action()
    #         participants[persona_id] = NPCState.READY
    #         return wait
    #     return None

    print("Registering custom on_ready and on_tick callbacks.")
    bridge.on_ready = on_ready
    # bridge.on_tick = on_tick

    async def on_action_complete(bridge, persona_id, action) -> Optional[Action]:
        nonlocal carol_state, participants
        return None

    bridge.on_action_complete = on_action_complete

    # Setup logging
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stdout,
        format="<%(levelname)s> %(asctime)s - %(name)s - %(pathname)s:%(lineno)d\n    %(message)s",
    )
    thistle_gulch.logger.setLevel(logging.INFO)
    # This shows the generation of the response as it comes in.
    fable_saga.streaming_debug_logger.setLevel(logging.DEBUG)

    try:
        bridge.run()
    except Exception as e:
        # Close the runtime if exception occurs.
        if bridge.runtime:
            bridge.runtime.terminate()
        raise e


if __name__ == "__main__":
    main()
