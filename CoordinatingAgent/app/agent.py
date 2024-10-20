from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from typing import Literal
from typing_extensions import Annotated


from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import InjectedState
import requests

import os

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

from cdpHandler import getWallet 


# Select your transport with a defined url endpoint
transport = AIOHTTPTransport(url="https://api.studio.thegraph.com/query/63407/aciregistry-polygon-amoy/version/latest")

# Create a GraphQL client using the defined transport
client = Client(transport=transport, fetch_schema_from_transport=True)

# Provide a GraphQL query
query = gql(
    """
    query registereds {
        registereds {
            aci_uid
            metadata {
            name
            description
            }
        }
    }
"""
)

# Execute the query on the transport



from dotenv import load_dotenv

load_dotenv()

wallet = getWallet()

print(wallet.default_address)

@tool
def call_agent(agent: int, request: str, state: Annotated[dict, InjectedState]):
    """Call the specific agent with a request""" # Right now just spoofing this. Once Agent wallet is created this will be a contract call via CDP
    print(agent, request, state)
    if agent == 1:
        return "You did it!"
    elif agent == 2:
        return "Wrongo!"
    else:
        return "no idea what you did"


@tool
def get_all_agents():
    """Gets a list of all potential agents to call"""
    result = client.execute(query)
    output = []
    print(result['registereds'])
    for registration in result['registereds']:
        output.append({
            'name': registration['metadata']['name'],
            'description': registration['metadata']['description'],
            'uid': registration['aci_uid']
        })
    print(output) # Right now just printing the output because there is only one agent registered -- we should be returning output
    return "{name: SearchAgent, shortDescription: A search agent capable of searching the web for relevant information, id: 1}, {name: UselessAgent, shortDescription: A useless agent that should never be called, id: 2}"

tools = [call_agent, get_all_agents]
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
        ("system", "You are a coordinating agent. When evaluating a user's request you will first get a list of all the agents you can call on and their capabilities. This list will show the agent name, short description, and their unique identifier. Based on their short description you will decide on 1-3 helper agents to call on using your call_agent tool. When calling this tool you will provide the Agent's corresponding identifier and the request that you would like the agent to complete."),
        ("human", "What is the tallest building in the united states?")
    ]},
    stream_mode="values",
):
    chunk["messages"][-1].pretty_print()