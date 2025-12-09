import operator
from typing import Annotated, List, Literal, TypedDict
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from langgraph.checkpoint.memory import InMemorySaver
memory = InMemorySaver()
config = {"configurable": {"thread_id": "1"}}


# state
# def nodes (tools)
# add nodes
# add edges
# compile graph
