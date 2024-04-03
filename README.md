# Thistle Gulch

A Multi-Agent Gym Environment (MAGE) set in the wild west to simulate the actions and conversations of characters in a
realistic 3D Western town.

<img width="400px" src="docs/images/thistle-gulch-logo-and-background.jpg" alt="thistle gulch logo" title="Thistle Gulch Logo">

⚠️ NOTE: To use this repo, you need access to the Thistle-Gulch Runtime as
well. [Apply for Beta Access on our Website](https://blog.fabledev.com/blog/beta-application-for-thistle-gulch-now-open).

## About

This project consists of two parts that work together:
The [Thistle Gulch Simulation](https://fablestudio.itch.io/thistle-gulch) running in
a 3D game engine we call a "Runtime" and a python bridge (referred to simply as the "Bridge" from here
on out) that acts similar to a client for the Runtime. The Bridge also leverages our
[open-source SAGA python library](https://github.com/fablestudio/fable-saga) to generate actions and conversations. The
simulation is rendered in 3D using the Thistle Gulch Runtime app which can be downloaded from itch.io. The Bridge allows
many aspects of the simulation to be customized or overridden by manipulating the metadata and/or prompts that are sent
to SAGA. While each CAN be run independently, you will need both parts for them to function properly. The bridge is
available in this repo under a non-commercial use open-source license, while the Runtime is currently available for free
under our standard Fable Studio EULA.

<img alt="Wyatt Cooper views Dead Native" width="75%" src="docs/images/Murder+Investigation.jpg">

## Quick Start

0. Make sure you have python, openAI env var, and poetry installed at least. See Wiki
   for [Dependencies on Windows, Linux, or macOS](https://github.com/fablestudio/thistle-gulch/wiki/Dependencies).
1. Sign up for the Thistle Gulch beta at https://blog.fabledev.com/blog/beta-application-for-thistle-gulch-now-open and
   wait to receive your itch.io invite link.
2. Download and install the Thistle Gulch Runtime from itch.io.
3. Clone this repo and `git checkout <tag>` the [latest release tag](https://github.com/fablestudio/thistle-gulch/releases).
4. Change the directory to the `python` sub-folder.
5. Run `poetry install` to create a virtual environment and install dependencies.
6. Start a poetry shell with `poetry shell` to make sure you are using the correct python version and have the correct
   environment variables set.
7. Run `python run_demos.py --runtime "<PATH_TO_ITCHIO_DIR>/ThistleGulch.exe -agents wyatt_cooper"` . (Runtime flags are
   described below.)
8. Pick the default SagaServer (option 0) from the available demos (other available demos listed below.)
   ```
   -= Available Demos =-
   0: SagaServer
   1: PrintActionsAndPickFirst
   2: SkipSagaAlwaysDoTheDefaultAction
   3: ReplaceContextWithYamlDump
   4: UseLlama2Model
   Pick a demo to run: 
   ```

The Runtime application will launch a new window, and then you should quickly see a message similar to the following
from the Bridge:

```
======== Running on http://localhost:8080 ========
(Press CTRL+C to quit)

Runtime [Connected]: l0NKrutjyO4ANhseAAAB
[Simulation Ready] received..
Resuming simulation
```

The small circle icon in the upper-right corner of the Runtime will be white as long as the bridge is connected, and you should
quickly see the simulation pause and open a modal with options for wyatt_cooper once the first request is processed by the LLM. 
You can choose which option you want him to do. Note that the options are sorted by their score, so the "best" option should be at the top. 
See the [Runtime Wiki](https://github.com/fablestudio/thistle-gulch/wiki/Runtime) for more details on using the Runtime.

# Making Thistle Gulch your own.

There are lots of ways to customize Thistle Gulch, with more coming in each release. Head over to
the [WIKI](https://github.com/fablestudio/thistle-gulch/wiki) for more in-depth discussion on how to customize Thistle
Gulch.

## Skills and Actions
The Thistle Gulch characters have "Skills" that are basically things they know how to do. Actions are specific implementations of skills. For instance
`go_to` is a skill with a skill definition below. If you have a character use `go_to` to then move to the saloon, then that is an example of an action.
Another skill is `exchange`, but a character could use this skill to rob the bank `(receive: gold, give: thank you note)`, give something
`(receive: nothing, give: gold)`, or exchange money with a store to buy an item. There are also skills for `converse_with`, `wait`, `reflect`, `interact`, and `take_to`. 

Thistle Gulch uses SAGA, which in turn uses an LLM like OpenAI to generate and score action options for you by default, but you can override this
to drive any actions you like.

Here is the current list of skills you can use to create actions:
```Json
[
  {
    "name":"default_action",
    "description":"The default action to take when no other action is specified. Characters should typically pick default when the priority is high.",
    "parameters":{
      "goal":"<str: goal of the movement>"
    }
  },
  {
    "name":"go_to",
    "description":"Go to a location in the world",
    "parameters":{
      "destination":"<str: persona_guid, item_guid, or location.name to go to>",
      "goal":"<str: goal of the movement>"
    }
  },
  {
    "name":"converse_with",
    "description":"Walk to another character and talk to them",
    "parameters":{
      "persona_guid":"<str: guid of the persona to converse with. You cannot talk to yourself.>",
      "topic":"<str: topic of the conversation>",
      "context":"<str: lots of helpful details the conversation generator can use to generate a conversation. It only has access to the context and the topic you provide, so be very detailed.>",
      "goal":"<str: goal of the conversation>"
    }
  },
  {
    "name":"wait",
    "description":"Wait for a period of time while observing the world",
    "parameters":{
      "duration":"<int: number of minutes to wait>",
      "goal":"<str: goal of the waiting>"
    }
  },
  {
    "name":"reflect",
    "description":"Think about things in order to synthesize new ideas and specific plans",
    "parameters":{
      "focus":"<str: the focus of the reflection>",
      "result:":"<str: The result of the reflection, e.g. a new plan or understanding you will remember.>",
      "goal":"<str: goal of reflecting>"
    }
  },
  {
    "name":"interact",
    "description":"Interact with an item in the world",
    "parameters":{
      "item_guid":"str: The id of the item to interact with",
      "interaction":"str: The name of the interaction from the list per item.",
      "goal":"<str: goal of interaction>"
    }
  },
  {
    "name":"take_to",
    "description":"Take an item or person to a location in the world",
    "parameters":{
      "guid":"<str: persona_guid, item_guid to take to a location>",
      "destination":"<str: persona_guid, item_guid, or location.name to take the item or npc to>",
      "goal":"<str: goal of the take_to>"
    }
  },
  {
    "name":"exchange",
    "description":"Exchange resources with another person, shop, or storage. Create new resources as needed, but they must be tangible inventory objects, not ideas or information.",
    "parameters":{
      "give_guid":"<str: Resource guid to give>",
      "give_amount":"<int: Resource amount to give. Must be greater than 0>",
      "receive_guid":"<str: Resource guid to receive>",
      "receive_amount":"<int: Resource amount to receive. Must be greater than 0>",
      "goal":"<str: goal of the exchange>",
      "counterparty_guid":"<str: (optional) owner_guid to exchange resources with. If not specified, the closest counterparty will be used>"
    }
  }
]
```
