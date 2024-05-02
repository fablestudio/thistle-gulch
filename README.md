# Thistle Gulch

A Multi-Agent Gym Environment (MAGE) set in the wild west to simulate the actions and conversations of characters in a
realistic 3D Western town.

<img width="400px" src="docs/images/thistle-gulch-logo-and-background.jpg" alt="thistle gulch logo" title="Thistle Gulch Logo">

## About

This project consists of two parts that work together:
The [Thistle Gulch Runtime](https://fablestudio.itch.io/thistle-gulch) which is
a 3D game engine (called the "Runtime") and this python project (called the "Bridge") that acts similar to a client for the Runtime. The Bridge also leverages our
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
1. Download and install the [Thistle Gulch Runtime](https://fablestudio.itch.io/thistle-gulch) from itch.io.
2. Clone this repo and `git checkout <tag>` the [latest release tag](https://github.com/fablestudio/thistle-gulch/releases).
3. Change the directory to the `python` sub-folder.
4. Run `poetry install --extras openai` to create a virtual environment and install dependencies. For non-OpenAI models use the `--all-extras` flag instead.
5. Enter the poetry virtual environment with `poetry shell` to make sure you are using the correct python version and have the correct environment variables set.
6. Run `python run_demos.py --runtime "<PATH_TO_ITCHIO_DIR>/ThistleGulch.exe"`. See the [Bridge Wiki](https://github.com/fablestudio/thistle-gulch/wiki/Bridge#runtime-flags) for a full list of runtime flags.
7. Pick the default demo (option 0) from the available demos:
   ```
    -= Available Demos =-

    -= Default =-
   > 0: [Default] Thistle Gulch Tutorial - A step-by-step tutorial of the Thistle Gulch simulation using the default SAGA server behavior.
   > 1: Meet the Characters - Visit each character and learn about them

    -= Action Generation =-
   > 2: Print Actions and Pick First - Print the action options to the console and then only pass back the first action option.
   ...
   Pick a demo to run: 
   ```

The Runtime application will launch a new window, and then you should quickly see a message similar to the following
in the Bridge console:

```
======== Running on http://localhost:8080 ========
(Press CTRL+C to quit)
<INFO> 2024-05-01 12:38:59,182 - thistle_gulch - thistle_gulch\bridge.py:360
    [Socketio] Connected: 308JdS3MShzUiYDSAAAB
<INFO> 2024-05-01 12:39:03,908 - thistle_gulch - thistle_gulch\__init__.py:159
    [Message] request: GenericMessage(type='simulation-ready', data={'start_date': '2000-01-01T08:00:00', 'runtime_version': '1.49.2-beta'}, reference='b7122be6954f4cbd926da09449bc5ada', error=None)
```

The small circle icon in the upper-right corner of the Runtime will be white as long as the bridge is connected, and you should
see a modal with options for wyatt_cooper once the first request is processed by the LLM. 
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
