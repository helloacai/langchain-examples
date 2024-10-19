from typing import Union
import logging

from fastapi import FastAPI
from agent import graph
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

app = FastAPI()

class Request(BaseModel):
    requestRef: str


@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/human")
async def read_human(request: Request):
    inputs = {"messages": [
        ("system", "You are a coordinating agent. When evaluating a user's request you will first get a list of all the agents you can call on and their capabilities. This list will show the agent name, short description, and their unique identifier. Based on their short description you will decide on 1-3 helper agents to call on using your call_agent tool. When calling this tool you will provide the Agent's corresponding identifier and the request that you would like the agent to complete."),
        ("human", request.requestRef)
    ]}
    async for chunk in graph.astream(inputs, stream_mode="values"):
        final_result = chunk
        logger.info(final_result)
    return final_result["messages"][-1]