# # Test agent to get use to it
#
# from app.core.config import settings
# import os
# import operator
# from typing import Annotated, Sequence, TypedDict
#
# from langchain_openai import ChatOpenAI
# from langgraph.graph import StateGraph, END
# from langgraph.prebuilt import ToolNode, tools_condition
# from langchain_core.messages import BaseMessage, HumanMessage
# from app.agents import agent_tools
#
#
# OPENAI_API_KEY = settings.OPENAI_API_KEY
#
# # TOOLS
# # get tools
# tools = agent_tools.xyz
#
# class AgentState(TypedDict):
#     messages: Annotated[Sequence[BaseMessage], operator.add]
#
# model = ChatOpenAI(
#     temperature=0.8,
#     model="gpt-4o-mini",
#     streaming=True
# )
#
# model_with_tools = model.bind_tools(tools)
#
# def call_model(state: AgentState):
#     print("Calling Model")
#     messages = state["messages"]
#     response = model_with_tools.invoke(messages)
#     return {"messages": [response]}
#
# workflow = StateGraph(AgentState)
#
# tool_node = ToolNode(tools)
#
# workflow.add_node("tools", tool_node)
# workflow.add_node("agent", call_model)
#
# workflow.set_entry_point("agent")
#
# workflow.add_conditional_edges(
#     "agent",
#     tools_condition,
#     {
#         "tools": "tools",
#         "__end__": END
#     }
# )
#
# workflow.add_edge("tools", "agent")
#
# app = workflow.compile()
#
# if __name__ == "__main__":
#     user_prompt = input("What is your question: ")
#
#     initial_input = {
#         "messages": [
#             HumanMessage(content=user_prompt)
#         ]
#     }
#
#     for output in app.stream(initial_input):
#         for key, value in output.items():
#             print(f"Output from node '{key}':")
#             print("---")
#             for message in value["messages"]:
#                 message.pretty_print()
#             print("\n---\n")