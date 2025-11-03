"""
Simple chat agent for testing CopilotKit integration
No tools, just basic conversation
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from typing import TypedDict, Sequence
from langgraph.checkpoint.memory import MemorySaver

# Define the state
class ChatState(TypedDict):
    messages: Sequence[BaseMessage]

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

def chat_node(state: ChatState) -> ChatState:
    """
    Simple chat node that responds to user messages
    """
    # Get the conversation history
    messages = state["messages"]
    
    # Call the LLM
    response = llm.invoke(messages)
    
    # Return updated state with the response
    return {
        "messages": messages + [response]
    }

# Create the graph
def create_chat_graph():
    """
    Create a simple chat graph with just one node
    """
    workflow = StateGraph(ChatState)
    
    # Add the chat node
    workflow.add_node("chat", chat_node)
    
    # Set entry point
    workflow.set_entry_point("chat")
    
    # Set finish point
    workflow.add_edge("chat", END)
    
    # Compile with memory
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
    
    return graph

# Create the graph instance
chat_graph = create_chat_graph()
