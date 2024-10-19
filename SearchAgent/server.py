from typing import Union
import logging

from fastapi import FastAPI
from agent import graph

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

app = FastAPI()


@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/human/{requestRef}")
async def read_human(requestRef: str):
    inputs = {"messages": [("human", requestRef)]}
    async for chunk in graph.astream(inputs, stream_mode="values"):
        final_result = chunk
        logger.info(final_result)
    return final_result["messages"][-1]