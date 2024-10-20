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

flow = Flow.from_client_secrets_file(
    './secrets/gcal_client_secrets.json',
    scopes=SCOPES,
    redirect_uri='urn:ietf:wg:oauth:2.0:oob')

@tool
def gcal_initiate_login():
    """initiate oath login to google calendar"""

    # Tell the user to go to the authorization URL.
    auth_url, _ = flow.authorization_url(prompt='consent')
    return "please login: "+auth_url

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


initialize = [gcal_initiate_login]
initialize_node = ToolNode(initialize)
login = [gcal_finalize_login]
login_node = ToolNode(login)
tools = [create_event]
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

def system_message():
    return SystemMessage(content="You are a google calendar event creation agent. The current datetime is "+datetime.now().isoformat()+" and your time zone is PST. When evaluating a user's request you will first need to log in to google with the gcal_initiate_login initializer. After calling this initializer you will need to ask the user to log in using the url provided by the tool. Once the user has logged in and responds with the code, you can use the gcal_finalize_login tool with the code to complete the login process. After that, use the create_event tool to create the requested event. When calling this tool you will provide the event's title, description, and datetime.")

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
