from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState, START, END
import requests

from datetime import datetime

import os

from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://polygon-amoy.g.alchemy.com/v2/FTsX20HJ4-N1XQicbeYKIjQSjHczteMp", request_kwargs={'timeout': 60}))

# Execute the query on the transport

from dotenv import load_dotenv

load_dotenv()

print("hi")

@tool
def reserve_restaurant(restaurant: int, time: datetime):
    """Call the specific agent with a request""" # Right now just spoofing this. Once Agent wallet is created this will be a contract call via CDP
    print(restaurant)
    if restaurant == 1:
        return "You did it!"
    elif restaurant == 2:
        return "Wrongo!"
    else:
        return "no idea what you did"


@tool
def get_all_restaurants():
    """Gets a list of all potential restaurants to reserve"""
    return "{name: Amber, cuisine: Indian shortDescription: yummy, id: 1}, {name: UselessRestaurant, cuisine: Chinese, shortDescription: chinese food, id: 2}"

tools = [reserve_restaurant, get_all_restaurants]
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

for chunk in graph.stream(
    {"messages": [
        ("system", "You are a restaurant reservation agent. When evaluating a user's request you will first get a list of all the restaurants you can reserve and their capabilities. This list will show the restaurant name, cuisine, short description, and their unique identifier. Based on their cuisine and short description you will decide on a restaurant to reserve using your reserve_restaurant tool. When calling this tool you will provide the Agent's corresponding identifier and the datetime for the reservation."),
        ("human", "I want to make a reservation for an indian restaurant at 7pm tomorrow PST")
    ]},
    stream_mode="values",
):
    chunk["messages"][-1].pretty_print()
