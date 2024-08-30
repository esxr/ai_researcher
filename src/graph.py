from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from .agents import generate_question, gen_answer
from .models import InterviewState, ResearchState

MAX_NUM_TURNS = 5;

def route_messages(state: InterviewState, name: str = "Subject_Matter_Expert"):
    messages = state["messages"]
    num_responses = len(
        [m for m in messages if isinstance(m, AIMessage) and m.name == name]
    )
    if num_responses >= MAX_NUM_TURNS:
        return END
    last_question = messages[-2]
    if last_question.content.endswith("Thank you so much for your help!"):
        return END
    return "ask_question"

def create_interview_graph():
    builder = StateGraph(InterviewState)
    builder.add_node("ask_question", generate_question)
    builder.add_node("answer_question", gen_answer)
    builder.add_conditional_edges("answer_question", route_messages)
    builder.add_edge("ask_question", "answer_question")
    builder.add_edge(START, "ask_question")
    return builder.compile()

interview_graph = create_interview_graph()

def create_storm_graph():
    builder = StateGraph(ResearchState)
    nodes = [
        ("init_research", initialize_research),
        ("conduct_interviews", conduct_interviews),
        ("refine_outline", refine_outline),
        ("index_references", index_references),
        ("write_sections", write_sections),
        ("write_article", write_article),
    ]
    for i in range(len(nodes)):
        name, node = nodes[i]
        builder.add_node(name, node)
        if i > 0:
            builder.add_edge(nodes[i - 1][0], name)
    builder.add_edge(START, nodes[0][0])
    builder.add_edge(nodes[-1][0], END)
    return builder.compile(checkpointer=MemorySaver())

storm = create_storm_graph()