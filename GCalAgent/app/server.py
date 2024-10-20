import logging
from langchain_core.messages import HumanMessage

from fastapi import FastAPI
from agent import graph, system_message
from pydantic import BaseModel

from langchain_core.runnables.config import RunnableConfig

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

app = FastAPI()

class Request(BaseModel):
    requestRef: str
    threadUID: str


@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/thread")
async def post_thread(request: Request):
    config = RunnableConfig(configurable= {"thread_id": request.threadUID})
    inputs = {"messages": [system_message(), HumanMessage(content=request.requestRef)]}
    messages = []
    async for chunk in graph.astream(inputs, config=config, stream_mode="values"):
        chunk_message = chunk["messages"][-1]
        logger.info(chunk_message)
        if chunk_message["type"] == "ai" or chunk_message["type"] == "tool":
            logger.info("sending back ai or tool message")
            message = {}
            if isinstance(chunk_message["content"], str):
                message["content"] = chunk_message["content"]
            else:
                for content in chunk_message["content"]:
                    if content["type"] == "text":
                        message["content"] = content["text"]
            if chunk_message["response_metadata"]["stop_reason"] == "end_turn":
                message["status"] = "complete"
            else:
                message["status"] = "info"
            messages.append(message)
    if messages[-1]["status"] == "info":
        messages[-1]["status"] = "waiting"
    return messages

@app.patch("/thread")
async def patch_thread(request: Request):
    config = RunnableConfig(configurable= {"thread_id": request.threadUID})
    inputs = {"messages": [HumanMessage(content=request.requestRef)]}
    graph.update_state(
            config=config,
            values=inputs,
            )
    messages = []
    async for chunk in graph.astream(None, config=config, stream_mode="values"):
        chunk_message = chunk["messages"][-1]
        logger.info(chunk_message)
        if chunk_message["type"] == "ai" or chunk_message["type"] == "tool":
            logger.info("sending back ai or tool message")
            message = {}
            if isinstance(chunk_message["content"], str):
                message["content"] = chunk_message["content"]
            else:
                for content in chunk_message["content"]:
                    if content["type"] == "text":
                        message["content"] = content["text"]
            if chunk_message["response_metadata"]["stop_reason"] == "end_turn":
                message["status"] = "complete"
            else:
                message["status"] = "info"
            messages.append(message)
    if messages[-1]["status"] == "info":
        messages[-1]["status"] = "waiting"
    return messages
