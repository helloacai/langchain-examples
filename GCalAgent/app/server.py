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
        messages.append(chunk)
        logger.info(chunk)
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
        messages.append(chunk)
        logger.info(chunk)
    return messages
