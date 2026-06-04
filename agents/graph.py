from langgraph.graph import StateGraph, END
from agents.state import AgenticSystemState
from agents.nodes import input_vision_agent, autonomous_retrieval_agent, autonomous_spatial_agent, conversational_synthesis_agent

def route_input_origin(state: AgenticSystemState):
    user_input = state["user_input"]
    if isinstance(user_input, str) and user_input.lower().endswith(('.png', '.jpg', '.jpeg')):
        return "vision_path"
    return "retrieval_path"

def route_post_retrieval(state: AgenticSystemState):
    if state.get("awaiting_confirmation"):
        return "halt"
    return "process_spatial_math"

workflow = StateGraph(AgenticSystemState)

workflow.add_node("InputVisionAgent", input_vision_agent)
workflow.add_node("RetrievalAgent", autonomous_retrieval_agent)
workflow.add_node("SpatialAgent", autonomous_spatial_agent)
workflow.add_node("SynthesisAgent", conversational_synthesis_agent)

workflow.set_conditional_entry_point(
    route_input_origin,
    {"vision_path": "InputVisionAgent", "retrieval_path": "RetrievalAgent"}
)

workflow.add_edge("InputVisionAgent", "RetrievalAgent")
workflow.add_conditional_edges(
    "RetrievalAgent",
    route_post_retrieval,
    {"halt": END, "process_spatial_math": "SpatialAgent"}
)
workflow.add_edge("SpatialAgent", "SynthesisAgent")
workflow.add_edge("SynthesisAgent", END)

agent_system = workflow.compile()