from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from langgraph.prebuilt import ToolNode
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState, START, END
import requests

from datetime import datetime
import json

import os

from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://polygon-amoy.g.alchemy.com/v2/FTsX20HJ4-N1XQicbeYKIjQSjHczteMp", request_kwargs={'timeout': 60}))

# Execute the query on the transport

from dotenv import load_dotenv

load_dotenv()

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

if __name__ == '__main__':
    config = RunnableConfig(configurable= {"thread_id": "1"})

    for chunk in graph.stream(
        {"messages": [
            ("system", "You are a restaurant reservation agent. When evaluating a user's request you will first get a list of all the restaurants you can reserve and their details. This list will show the restaurant id, name, categories, and description among other details. Based on their categories, description, and other details you will decide on a restaurant to reserve using your reserve_restaurant tool. When calling this tool you will provide the restaurant dict and the datetime for the reservation."),
            ("human", "I want to make a reservation for a good indian restaurant in San Francisco at 7pm tomorrow PST")
        ]},
        config=config,
        stream_mode="values",
    ):
        chunk["messages"][-1].pretty_print()
