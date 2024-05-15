import asyncio
import sys
from datetime import datetime, timedelta
from typing import List, Dict
import logging

import cattrs
from langchain.prompts import PromptTemplate
import fable_saga.server

import thistle_gulch.bridge
from thistle_gulch.data_models import ModelConfig
from thistle_gulch.skills import GoToSkill, ConverseWithSkill, ReflectSkill

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
    people they've decided on. They will use their skills to try to convince the people to join the Carol.
    
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


def main():
    bridge = thistle_gulch.bridge.main(auto_run=False)

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

    carol_time = datetime(1890, 12, 24, 18, 0, 0)
    carol_state = "not_started"
    singers: Dict[str, str] = {"sarah_brown": "returning", "ezekiel_blackwood": "waiting"}
    organizers = ["sarah_brown", "ezekiel_blackwood"]

    async def on_ready(_, world_context):

        print("Setting the time to Christmas Eve Day.")
        nonlocal carol_time
        await bridge.runtime.api.set_start_date(carol_time - timedelta(hours=0.5))
        print("Time set.")
        singers["ezekiel_blackwood"] = "waiting"
        singers["sarah_brown"] = "returning"

        initial_conversation = ConverseWithSkill(
            persona_guid="ezekiel_blackwood",
            topic="Recruiting Singers for the Christmas Carol",
            context="Christmas Carol",
            goal="Recruit Singers",
            conversation=None,
        )
        await bridge.runtime.api.override_character_action("sarah_brown", initial_conversation.to_action())


        future = asyncio.Future()
        await bridge.runtime.api.modal("The Christmas Carol", guidance, ["Start"], False, future)
        await future

        await bridge.runtime.api.resume()

    async def on_tick(_, current_time: datetime):
        nonlocal carol_time, carol_state, singers
        # Only trigger the arrest once at the designated time
        if current_time < carol_time:
            return

        elif carol_state == "not_started":
            await bridge.runtime.api.modal("Gather up", "Gather round, the Christmas Carol is about to begin!")
            carol_state = "waiting"
            for person in singers:
                goto = GoToSkill(goal="Join the Christmas Carol", destination="church")
                await bridge.runtime.api.override_character_action(person, goto.to_action())

        elif carol_state == "starting":
            carol_state = "started"
            await bridge.runtime.api.modal("Everyone has arrived", "The Christmas Carol has started!")
            line = "We wish you a merry Christmas!"
            wait_for = []
            for person in singers:
                # TODO: Looks like converse_with doesn't work with a single character in the Runtime.
                # Basically, it assumes a companion character, so we need to use ReflectSkill instead.
                # singing_convo = ConverseWithSkill(
                #     persona_guid=person,
                #     conversation=[{"persona_guid":person, "dialogue": line} for i in range(3)],
                #     topic="Singing",
                #     context="Christmas Carol",
                #     goal="Sing the Christmas Carol",
                # )
                singing = ReflectSkill(focus="Sing a Christmas Carol to yourself", result="3 lines of a christmas carol were sung", goal="Sing the Carol")
                future = asyncio.Future()
                await bridge.runtime.api.override_character_action(person, singing.to_action(), future)
                wait_for.append(future)
            await asyncio.gather(*wait_for)
            carol_state = "stopping"
        elif carol_state == "ending":
            print("The Christmas Carol has ended!")
            await bridge.runtime.api.modal("The End", "The Christmas Carol has ended!", None)
            carol_state = "ended"

    async def on_action_complete(_, persona_id, action):
        nonlocal carol_state, singers
        if persona_id not in singers:
            return
        if carol_state == "not_started":
            if persona_id in organizers and singers[persona_id] == "returning":
                singers[persona_id] = "waiting"

        if carol_state == "waiting":
            singers[persona_id] = "ready"
            if all([singers[persona] == "ready" for persona in singers]):
                carol_state = "starting"
        elif carol_state == "starting":
            singers[persona_id] = "done"
            if all([singers[persona] == "done" for persona in singers]):
                carol_state = "ending"

    print("Registering custom on_ready and on_tick callbacks.")
    bridge.on_ready = on_ready
    bridge.on_tick = on_tick
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
