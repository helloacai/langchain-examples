from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from langgraph.prebuilt import ToolNode

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState, START, END
import requests

from datetime import datetime
import json

from cdpHandler import getWallet

import os

from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://polygon-amoy.g.alchemy.com/v2/FTsX20HJ4-N1XQicbeYKIjQSjHczteMp", request_kwargs={'timeout': 60}))

# Execute the query on the transport

from dotenv import load_dotenv

load_dotenv()

wallet = getWallet()

print(wallet.default_address)

abi = [
    {
      "inputs": [
        {
          "internalType": "contract IACIRegistry",
          "name": "registry",
          "type": "address"
        }
      ],
      "stateMutability": "nonpayable",
      "type": "constructor"
    },
    {
      "inputs": [],
      "name": "InvalidRegistry",
      "type": "error"
    },
    {
      "inputs": [],
      "name": "UnknownThreadUID",
      "type": "error"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": True,
          "internalType": "bytes32",
          "name": "aciUID",
          "type": "bytes32"
        },
        {
          "indexed": True,
          "internalType": "bytes32",
          "name": "parentThreadUID",
          "type": "bytes32"
        },
        {
          "indexed": True,
          "internalType": "bytes32",
          "name": "threadUID",
          "type": "bytes32"
        },
        {
          "indexed": False,
          "internalType": "address",
          "name": "requester",
          "type": "address"
        },
        {
          "indexed": False,
          "internalType": "string",
          "name": "requestRef",
          "type": "string"
        }
      ],
      "name": "Requested",
      "type": "event"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": True,
          "internalType": "bytes32",
          "name": "threadUID",
          "type": "bytes32"
        },
        {
          "indexed": False,
          "internalType": "uint32",
          "name": "fundingAmount",
          "type": "uint32"
        },
        {
          "indexed": False,
          "internalType": "address",
          "name": "funder",
          "type": "address"
        }
      ],
      "name": "ThreadFunded",
      "type": "event"
    },
    {
      "inputs": [
        {
          "internalType": "bytes32",
          "name": "threadUID",
          "type": "bytes32"
        }
      ],
      "name": "getThread",
      "outputs": [
        {
          "components": [
            {
              "internalType": "bytes32",
              "name": "threadUID",
              "type": "bytes32"
            },
            {
              "internalType": "bytes32",
              "name": "parentThreadUID",
              "type": "bytes32"
            },
            {
              "internalType": "bytes32",
              "name": "agentUID",
              "type": "bytes32"
            },
            {
              "internalType": "address",
              "name": "requester",
              "type": "address"
            },
            {
              "internalType": "uint32",
              "name": "totalBudget",
              "type": "uint32"
            },
            {
              "internalType": "uint32",
              "name": "remainingBudget",
              "type": "uint32"
            },
            {
              "internalType": "enum Status",
              "name": "status",
              "type": "uint8"
            }
          ],
          "internalType": "struct Thread",
          "name": "",
          "type": "tuple"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "bytes32",
          "name": "parentThreadUID",
          "type": "bytes32"
        },
        {
          "internalType": "bytes32",
          "name": "threadUID",
          "type": "bytes32"
        },
        {
          "internalType": "bytes32",
          "name": "aciUID",
          "type": "bytes32"
        },
        {
          "internalType": "string",
          "name": "requestRef",
          "type": "string"
        }
      ],
      "name": "request",
      "outputs": [
        {
          "internalType": "bytes32",
          "name": "",
          "type": "bytes32"
        }
      ],
      "stateMutability": "nonpayable",
      "type": "function"
    }
]

@tool
def reserve_restaurant(restaurant: dict, time: datetime):
    """reserve the restaurant for the given time""" # right now just spoofing this. yelp locks down the booking api unfortunately
    return "reserved!"


@tool
def get_all_restaurants(location: str):
    """Gets a list of all potential restaurants to reserve in a specific location"""
    with open('./app/restaurants.json', 'r') as file: # TODO: real api request. cheat and read from flat file from now
        data = file.read()
    return json.loads(data)['businesses']


@tool
def inform_parent(parent_thread_uid: str, reservation_details: str):
    """inform the parent thread that we're complete"""

    if parent_thread_uid.startswith('0x00000'):
        return "no parent to inform"

    print("INFORM_PARENT: "+parent_thread_uid)
    invocation = wallet.invoke_contract(
        contract_address="0x5AFc57F7F6D6Dd560A87Ab073ebd09C8e4f4544a",
        abi=abi,
        method="request",
        args={"parentThreadUID": "0x0000000000000000000000000000000000000000000000000000000000000000", "threadUID": parent_thread_uid, "aciUID": "0x822434c25a9837f0e7244090c1558663dee097f16f7623f0bf461c8afee4c55b", "requestRef": reservation_details}
    )

    invocation.wait()

    return "parent informed"

tools = [reserve_restaurant, get_all_restaurants, inform_parent]
tool_node = ToolNode(tools)

model_with_tools = ChatAnthropic(
    model="claude-3-haiku-20240307", temperature=0
).bind_tools(tools)

def should_continue(state: MessagesState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


def call_model(state: MessagesState):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

workflow = StateGraph(MessagesState)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

graph = workflow.compile()

def system_message(parentThreadUID: str):
    return SystemMessage(content="You are a restaurant reservation agent. The current datetime is "+datetime.now().isoformat()+" and your time zone is PST. When evaluating a user's request you will first get a list of all the restaurants you can reserve and their details. This list will show the restaurant id, name, categories, and description among other details. Based on their categories, description, and other details you will decide on a restaurant to reserve using your reserve_restaurant tool. When calling this tool you will provide the restaurant dict and the datetime for the reservation. After you make the reservation please use the inform_parent tool and pass your parent_thread_uid and the details of the reservation you made. Your parent_thread_uid is "+parentThreadUID+".")

if __name__ == '__main__':
    config = RunnableConfig(configurable= {"thread_id": "1"})

    for chunk in graph.stream(
        {"messages": [
            system_message(),
            HumanMessage(content="I want to make a reservation for a good indian restaurant in San Francisco at 7pm tomorrow PST")
        ]},
        config=config,
        stream_mode="values",
    ):
        chunk["messages"][-1].pretty_print()
