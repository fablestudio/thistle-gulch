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
from thistle_gulch.data_models import ModelConfig, WorldContextObject, Vector3
from thistle_gulch.skills import GoToSkill, ConverseWithSkill, ReflectSkill, Action


# Change the guidance to a Christmas Carol.
guidance = (
    "It's Christmas Eve in Thistle Gulch. The town is depressed and the people are poor, but Reverend Blackwood wants"
    " to change that. He's planning a Christmas Carol for the town, but he needs to gather some people to help him."
    " He's looking for a few good people to help him spread some Christmas cheer, or so he says."
    " Sarah Brown has wearily agreed to help by convincing others in town to join the Carol. She's not sure if it"
    " will work, given the town's mood, but she's willing to try."
    "\n"
    "Each character (blackwood or brown) has a different set of skills that they can use. First the two characters will"
    " discuss who to recruit and which one of them will do the recruiting. Then they will go out and try to recruit the"
    " people they've decided on. They will use their skills to try to convince the people to join the Carol. Each"
    " person they try to convince will state whether they will join or not. If they join, they will return to their"
    " normal activities until the Carol starts at 6pm. They will not offer to recruit anyone else. Characters can and"
    " should refuse to join the Carol if they are busy or if it's out of character."
    "\n"
    " At 6pm, the Carol will start. The goal is to have as many people as possible join the Carol. The more people that"
    " join, the more successful the Carol will be. The Carol will last for 1 hour, and then the story will end."
)


class CustomConversationEndpoint(thistle_gulch.bridge.TGConversationEndpoint):

    # TODO: This is a little clunky, but it works for now. We need to override the handle_request method to replace the
    #  murder guidance with the Christmas Carol guidance.
    async def handle_request(self, request: thistle_gulch.bridge.TGConversationRequest):
        request.context = guidance + "\nTASK:\n" + request.context.split("\nTask:")[1]
        request.model = None
        return await super().handle_request(request)


class NPCState(Enum):
    NOT_INVITED = "not invited yet"
    JOINING = "plans to join"
    DECLINED = "declined invitation"


def main():
    # SETUP
    bridge = thistle_gulch.bridge.main(auto_run=False)
    zoom_level = 0.6

    carol_time = datetime(1890, 12, 24, 18, 0, 0)
    current_time = carol_time
    organizers = ["sarah_brown", "ezekiel_blackwood"]
    participants: Dict[str, NPCState] = {name: NPCState.JOINING for name in organizers}

    # Create a custom conversation agent for the Christmas Carol - we will change the template later.
    llm = thistle_gulch.bridge.dynamic_model_loader(
        cattrs.structure(bridge.config.conversation_llm, ModelConfig)
    )
    conversation_agent = thistle_gulch.bridge.ConversationAgent(llm=llm)

    # Create the override endpoints (we may not need both).
    override_conversations = thistle_gulch.bridge.Route(
        thistle_gulch.IncomingRoutes.generate_conversations.value,
        CustomConversationEndpoint(conversation_agent),
    )
    # Override the conversation endpoint.
    bridge.router.add_route(override_conversations)

    # HELPER FUNCTIONS
    async def wait_action(npc: str, action: Action, wait_for_next: bool = True) -> None:
        future = asyncio.get_event_loop().create_future()
        await bridge.runtime.api.override_character_action(
            npc, action, future, wait=wait_for_next
        )
        await future

    async def wait_modal(
        title: str, message: str, buttons: Optional[List[str]], pause: bool
    ) -> None:
        future = asyncio.get_event_loop().create_future()
        await bridge.runtime.api.modal(title, message, buttons, pause, future)
        await future

    async def follow_and_focus_on(persona: str):
        await bridge.runtime.api.follow_character(persona, zoom_level)
        await bridge.runtime.api.focus_character(
            persona, bridge.runtime.api.FocusPanelTab.COLLAPSED
        )

    # MAIN TASKS
    async def plan_and_recruit():
        nonlocal organizers, participants

        persona_id = organizers[0]
        await follow_and_focus_on(persona_id)
        other_organizer = [org for org in organizers if org != persona_id][0]
        await wait_action(
            persona_id,
            ConverseWithSkill(
                persona_guid=other_organizer,
                topic="Recruiting Singers for the Christmas Carol this evening",
                context="Christmas Carol",
                goal="Pick a new person to recruit and which character will do the recruiting.",
                conversation=None,
            ).to_action(),
        )

        # Get the result of the conversation and define the next action.
        ctx = await bridge.runtime.api.get_world_context()
        convo = ctx.conversations[-1]
        prompt = (
            "TRANSCRIPT:\n"
            + json.dumps(cattrs.unstructure(convo.transcript))
            + "\n"
            + "PERSONAS:\n"
            + "\n".join(
                [
                    f"{p.persona_guid}: {participants[persona_id].value}"
                    for p in ctx.personas
                ]
            )
            + "\n"
            + "TASK:\n"
            + "Based on the transcript, convert what the characters decided to do into the following JSON format:"
            + ' {"plans": [recruiter_id: <persona_guid>, "recruit_ids": [<persona_guid>]}'
        )
        result: AIMessage = await llm.ainvoke(prompt)  # type: ignore
        if not isinstance(result.content, str):
            raise ValueError("Expected a string response from the model.")

        # Execute the plan to recruit the singers.
        plans: List[Dict[str, Any]] = json.loads(result.content)["plans"]
        # Note: we could have used asyncio.gather here, but it's a little chaotic to have both characters talking at once.
        for plan in plans:
            non_recruiter = [org for org in organizers if org != plan["recruiter_id"]][
                0
            ]
            goto_meeting_place = GoToSkill(
                goal="Wait for other Organizer",
                destination="thistle_gulch.outside_saloon",
            ).to_action()
            # Have the non-recruiter wait for the recruiter to finish.
            await bridge.runtime.api.override_character_action(
                non_recruiter, goto_meeting_place, None, wait=True
            )
            # Have the recruiter go recruit the people.
            await follow_and_focus_on(plan["recruiter_id"])
            await go_recruit(plan["recruiter_id"], plan["recruit_ids"])

    async def go_recruit(recruiter: str, targets: List[str]):
        nonlocal participants
        for target in targets:
            if current_time >= carol_time:
                break
            conversation = ConverseWithSkill(
                persona_guid=target,
                topic="Joining the Christmas Carol",
                context=f"{recruiter} is trying to get {target} to join the Christmas Carol, but they may say no.",
                goal="Convince the person to join the Christmas Carol.",
                conversation=None,
            ).to_action()
            await wait_action(recruiter, conversation)

            # Was the conversation successful? If so, set the target to ready.
            ctx = await bridge.runtime.api.get_world_context()
            convo = ctx.conversations[-1]
            prompt = (
                "TRANSCRIPT:\n"
                + json.dumps(cattrs.unstructure(convo.transcript))
                + "\n"
                + "TASK:\n"
                + "Based on the transcript, convert what the characters decided to do into the following JSON format:"
                + ' {"decided_to_join": <bool>}'
            )

            result: AIMessage = await llm.ainvoke(prompt)  # type: ignore
            print(result.content)
            if not isinstance(result.content, str):
                raise ValueError("Expected a string response from the model.")

            decision: Dict[str, Any] = json.loads(result.content)
            if decision["decided_to_join"]:
                participants[target] = NPCState.JOINING
            else:
                participants[target] = NPCState.DECLINED

    # OVERRIDE ON_READY AND DRIVE STORY VIA AWAITS
    async def on_ready(_: RuntimeBridge, world_context: WorldContextObject):
        nonlocal carol_time, current_time, organizers, participants

        # Disable all agents except the organizers and even then, only enable the conversation agent for each.
        for persona in world_context.personas:
            await bridge.runtime.api.enable_agent(
                persona.persona_guid, False, persona.persona_guid in organizers
            )
            # Add the rest of the participants to the list as uninvited.
            if persona.persona_guid not in organizers:
                participants[persona.persona_guid] = NPCState.NOT_INVITED

        # Set initial character positions.
        await bridge.runtime.api.place_character(
            organizers[0], Vector3(1, 0, 0), Vector3(0, 0, 0)
        )
        await bridge.runtime.api.place_character(
            organizers[1], Vector3(-1, 0, 0), Vector3(0, 180, 0)
        )
        await follow_and_focus_on(organizers[0])

        # Set them both to waiting, so they don't go anywhere unless instructed.
        await bridge.runtime.api.override_character_action(
            organizers[0], None, None, wait=True
        )
        await bridge.runtime.api.override_character_action(
            organizers[1], None, None, wait=True
        )

        print("Setting the time to Christmas Eve Day.")
        current_time = carol_time - timedelta(hours=5)
        await bridge.runtime.api.set_start_date(current_time)
        print("Time set.")

        # TODO: Add memories for the characters of why they are doing this.

        await wait_modal("The Christmas Carol", guidance, ["Start"], False)
        await bridge.runtime.api.resume()

        while carol_time > current_time:
            await plan_and_recruit()

        # Time to gather everyone at the church.
        await wait_modal(
            "Gather up",
            "Gather round, the Christmas Carol is about to begin!",
            ["Start"],
            True,
        )
        goto_church = GoToSkill(
            goal="Join the Christmas Carol", destination="church"
        ).to_action()
        # asyncio.gather will run all the actions concurrently, but wait for all of them to finish before continuing.
        await asyncio.gather(
            *[
                wait_action(persona, goto_church)
                for persona in participants
                if participants[persona] == NPCState.JOINING
            ]
        )

        # Start the carol.
        await wait_modal(
            "The Christmas Carol", "The Christmas Carol has started!", None, True
        )
        # TODO: It would be nice to have the characters sing a Christmas Carol, but there isn't a way to have a
        #  conversation with oneself at the moment where the lines can be provided ahead of time.

        await wait_modal(
            "Everyone Sings!",
            "We wish you a merry Christmas..\n\nWe wish you a merry Christmas..",
            ["Complete"],
            True,
        )

        # Release everyone to go about their normal routines.
        for p in participants.keys():
            if participants[p] == NPCState.JOINING:
                await bridge.runtime.api.override_character_action(
                    p, None, None, wait=False
                )

        final_convo = ConverseWithSkill(
            persona_guid=organizers[1],
            topic="The Christmas Carol",
            context="The Christmas Carol has ended and the town is in good spirits.",
            goal="Discuss the success of the Christmas Carol.",
            conversation=None,
        ).to_action()
        await wait_action(organizers[0], final_convo)

    async def on_tick(_, tick_time: datetime):
        nonlocal current_time
        # Update the current time.
        current_time = tick_time

    # Set the on_ready and on_tick callbacks.
    bridge.on_ready = on_ready
    bridge.on_tick = on_tick

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
