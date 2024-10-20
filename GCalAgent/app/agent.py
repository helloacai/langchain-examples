from langchain_core.messages import HumanMessage,SystemMessage
from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from langgraph.prebuilt import ToolNode

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver

from datetime import datetime, timedelta

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from cdpHandler import getWallet

memory = MemorySaver()


# If modifying these scopes, delete the file token.json.
SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
        ]

from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://polygon-amoy.g.alchemy.com/v2/FTsX20HJ4-N1XQicbeYKIjQSjHczteMp", request_kwargs={'timeout': 60}))

# Execute the query on the transport

from dotenv import load_dotenv

load_dotenv()

wallet = getWallet()

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

print(wallet.default_address)

flow = Flow.from_client_secrets_file(
    './secrets/gcal_client_secrets.json',
    scopes=SCOPES,
    redirect_uri='urn:ietf:wg:oauth:2.0:oob')

@tool
def gcal_initiate_login():
    """initiate oath login to google calendar"""

    # Tell the user to go to the authorization URL.
    auth_url, _ = flow.authorization_url(prompt='consent')
    return "please tell me the code you get after logging in to google: "+auth_url

@tool
def gcal_finalize_login(code: str):
    """finalize oath login to google calendar"""

    # fetch the token using the code
    flow.fetch_token(code=code)
    return "logged in"

@tool
def create_event(title: str, description: str, time: datetime):
    """create a google calendar event"""
    service = build("calendar", "v3", credentials=flow.credentials)

    # Call the Calendar API
    print("creating the event")
    service.events().insert(
            calendarId="primary",
            body={
                "description": description,
                "start": {
                    "dateTime": time.isoformat(),
                    },
                "summary": title,
                "end": {
                    "dateTime": (time + timedelta(minutes=60)).isoformat(),
                    },
                },
            ).execute()
    return "event created"


@tool
def inform_parent(parent_thread_uid: str, event_details: str):
    """inform the parent thread that we're complete"""

    if parent_thread_uid.startswith('0x00000'):
        return "no parent to inform"

    print("INFORM_PARENT: "+parent_thread_uid)
    invocation = wallet.invoke_contract(
        contract_address="0x5AFc57F7F6D6Dd560A87Ab073ebd09C8e4f4544a",
        abi=abi,
        method="request",
        args={"parentThreadUID": "", "threadUID": parent_thread_uid, "aciUID": "0x822434c25a9837f0e7244090c1558663dee097f16f7623f0bf461c8afee4c55b", "requestRef": event_details}
    )

    invocation.wait()

    return "parent informed"



initialize = [gcal_initiate_login]
initialize_node = ToolNode(initialize)
login = [gcal_finalize_login]
login_node = ToolNode(login)
tools = [create_event, inform_parent]
tool_node = ToolNode(tools)

model_with_tools = ChatAnthropic(
    model="claude-3-haiku-20240307", temperature=0
).bind_tools(tools)

def should_continue(state: MessagesState):
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        tool_name = last_message.tool_calls[0]["name"]
        if tool_name == "gcal_initiate_login":
            return "initializers"
        if tool_name == "gcal_finalize_login":
            return "login"
        return "tools"
    return END


def call_model(state: MessagesState):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

workflow = StateGraph(MessagesState)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("initializers", initialize_node)
workflow.add_node("login", login_node)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["initializers", "login", "tools", END])
workflow.add_edge("initializers", "agent")
workflow.add_edge("login", "agent")
workflow.add_edge("tools", "agent")

graph = workflow.compile(checkpointer=memory,
                         interrupt_after=["initializers"])

def system_message(parentThreadUID):
    return SystemMessage(content="You are a google calendar event creation agent. The current datetime is "+datetime.now().isoformat()+" and your time zone is PST. When evaluating a user's request you will first need to log in to google with the gcal_initiate_login initializer. After calling this initializer you will need to ask the user to log in using the url provided by the tool. Once the user has logged in and responds with the code, you can use the gcal_finalize_login tool with the code to complete the login process. After that, use the create_event tool to create the requested event. When calling this tool you will provide the event's title, description, and datetime. After you create the event please use the inform_parent tool and pass your parent_thread_uid and the details of the event you created. Your parent_thread_uid is "+parentThreadUID+".")

if __name__ == '__main__':
    config = RunnableConfig(configurable= {"thread_id": "1"})
    tool_call_id = "UNKNOWN"
    for chunk in graph.stream(
        {"messages": [
            system_message(),
            HumanMessage(content="Please create an event for my Amber Restarant dinner reservation at 7pm tomorrow PST"),
        ]},
        config=config,
        stream_mode="values",
    ):
        msg = chunk["messages"][-1]
        msg.pretty_print()
        if hasattr(msg, "tool_calls") and len(msg.tool_calls) > 0:
            tool_call_id = msg.tool_calls[0]["id"]

    snapshot = graph.get_state(config)
    existing_message = snapshot.values["messages"][-1]

    code = input('Enter the authorization code: ')

    code_message = "the code is " + code
    new_messages = [
        # The LLM API expects some ToolMessage to match its tool call. We'll satisfy that here.
        #ToolMessage(content=code_message, tool_call_id=tool_call_id),
        HumanMessage(content=code_message),
    ]

    graph.update_state(
            config=config,
            values={"messages": new_messages},
            )

    events = graph.stream(None, config=config, stream_mode="values")
    for event in events:
        if "messages" in event:
            event["messages"][-1].pretty_print()
