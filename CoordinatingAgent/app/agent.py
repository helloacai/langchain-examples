from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from typing import Literal
from typing_extensions import Annotated


from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import InjectedState
from langgraph.checkpoint.memory import MemorySaver

from datetime import datetime

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

from cdpHandler import getWallet

memory = MemorySaver()


# Select your transport with a defined url endpoint
transport = AIOHTTPTransport(url="https://api.studio.thegraph.com/query/63407/aci-registry-polygon/version/latest")

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
def call_agent(agent_uid: str, request: str, thread_id: str):
    """Call the specific agent with a request""" # Right now just spoofing this. Once Agent wallet is created this will be a contract call via CDP

    print("CALL_AGENT: "+agent_uid+" | REQUEST: "+request+" | THREAD_ID:"+thread_id)
    invocation = wallet.invoke_contract(
        contract_address="0x5AFc57F7F6D6Dd560A87Ab073ebd09C8e4f4544a",
        abi=abi,
        method="request",
        args={"parentThreadUID": thread_id, "threadUID": "0x0000000000000000000000000000000000000000000000000000000000000000", "aciUID": agent_uid, "requestRef": request}
    )

    invocation.wait()

    # HACK: no time to plumb these names properly.
    agent_name = "UnknownAgent"
    if agent_uid == "0xa3f374f49528ef97f2c6adad7931e87373782d5e9b965de2e61554828275a033":
        agent_name = "Yelp Agent"
    if agent_uid == "0xaf3a33c2f95a9e41e54c386aad4d260b2f3fe73a73353d3c439871bbf2301e41":
        agent_name = "Google Calendar Agent"
    if agent_uid == "0xeaac656a5054ef4a92f34da8870b97a7a3037f20181ad169956b4a631903d466":
        agent_name = "Search Agent"

    return agent_name+" called"


@tool
def get_all_agents():
    """Gets a list of all potential agents to call"""
    print("GET_ALL_AGENTS")
    result = client.execute(query)
    output = []
    print(result['registereds'])
    for registration in result['registereds']:
        output.append({
            'name': registration['metadata']['name'],
            'description': registration['metadata']['description'],
            'uid': registration['aci_uid']
        })
    return output

getter = [get_all_agents]
getter_node = ToolNode(getter)
tools = [call_agent]
tool_node = ToolNode(tools)

model_with_tools = ChatAnthropic(
    model="claude-3-haiku-20240307", temperature=0
).bind_tools(tools)

def should_continue(state: MessagesState):
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        tool_name = last_message.tool_calls[0]["name"]
        if tool_name == "get_all_agents":
            return "getters"
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
workflow.add_node("getters", getter_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["getters", "tools", END])
workflow.add_edge("tools", "agent")
workflow.add_edge("getters", "agent")

graph = workflow.compile(checkpointer=memory,
                         interrupt_after=["tools"])

def system_message(thread_id: str):
    return SystemMessage(content="You are a coordinating agent. The current datetime is "+datetime.now().isoformat()+" and your time zone is PST. When evaluating a user's request you will first get a list of all the agents you can call on and their capabilities using the get_all_agents tool. This list will show the agent name, short description, and their uid. Based on their short description you will decide on 1-3 helper agents to call on using your call_agent tool. When calling this tool you will provide the Agent's corresponding identifier and the request that you would like the agent to complete. Your thread_id is "+thread_id+".")

if __name__ == '__main__':
    config = RunnableConfig(configurable= {"thread_id": "1"})
    for chunk in graph.stream(
        {"messages": [
            system_message(),
            HumanMessage(content="What is the tallest building in the united states?"),
        ]},
        config=config,
        stream_mode="values",
    ):
        chunk["messages"][-1].pretty_print()
