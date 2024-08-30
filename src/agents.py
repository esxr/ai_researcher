import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, chain as as_runnable
from langchain_community.retrievers import WikipediaRetriever
from langchain_community.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from typing import List, Optional

from .models import (
    Outline,
    Editor,
    Perspectives,
    Queries,
    AnswerWithCitations,
    RelatedSubjects,
    InterviewState
)
from .prompts import (
    direct_gen_outline_prompt,
    gen_perspectives_prompt,
    gen_qn_prompt,
    gen_answer_prompt,
    gen_related_topics_prompt,
    gen_queries_prompt,
)
from .utils import format_docs, tag_with_name, swap_roles

fast_llm = ChatOpenAI(model="gpt-3.5-turbo")
long_context_llm = ChatOpenAI(model="gpt-4-turbo-preview")

generate_outline_direct = direct_gen_outline_prompt | fast_llm.with_structured_output(
    Outline
)

gen_queries_chain = gen_queries_prompt | ChatOpenAI(
    model="gpt-3.5-turbo"
).with_structured_output(Queries, include_raw=True)

gen_perspectives_chain = gen_perspectives_prompt | ChatOpenAI(
    model="gpt-3.5-turbo"
).with_structured_output(Perspectives)

wikipedia_retriever = WikipediaRetriever(load_all_available_meta=True, top_k_results=1)

gen_answer_chain = gen_answer_prompt | fast_llm.with_structured_output(
    AnswerWithCitations, include_raw=True
).with_config(run_name="GenerateAnswer")

expand_chain = gen_related_topics_prompt | fast_llm.with_structured_output(
    RelatedSubjects
)


@as_runnable
async def survey_subjects(topic: str):
    related_subjects = await expand_chain.ainvoke({"topic": topic})
    retrieved_docs = await wikipedia_retriever.abatch(
        related_subjects.topics, return_exceptions=True
    )
    all_docs = []
    for docs in retrieved_docs:
        if isinstance(docs, BaseException):
            continue
        all_docs.extend(docs)
    formatted = format_docs(all_docs)
    return await gen_perspectives_chain.ainvoke({"examples": formatted, "topic": topic})


@as_runnable
async def generate_question(state: InterviewState):
    editor = state["editor"]
    gn_chain = (
        RunnableLambda(swap_roles).bind(name=editor.name)
        | gen_qn_prompt.partial(persona=editor.persona)
        | fast_llm
        | RunnableLambda(tag_with_name).bind(name=editor.name)
    )
    result = await gn_chain.ainvoke(state)
    return {"messages": [result]}


search_engine = DuckDuckGoSearchAPIWrapper()

@tool
async def search_engine(query: str):
    """Search engine to the internet."""
    results = DuckDuckGoSearchAPIWrapper()._ddgs_text(query)
    return [{"content": r["body"], "url": r["href"]} for r in results]


async def gen_answer(
    state: InterviewState,
    config: Optional[RunnableConfig] = None,
    name: str = "Subject_Matter_Expert",
    max_str_len: int = 15000,
):
    swapped_state = swap_roles(state, name)
    queries = await gen_queries_chain.ainvoke(swapped_state)
    query_results = await search_engine.abatch(
        queries["parsed"].queries, config, return_exceptions=True
    )
    successful_results = [
        res for res in query_results if not isinstance(res, Exception)
    ]
    all_query_results = {
        res["url"]: res["content"] for results in successful_results for res in results
    }
    dumped = json.dumps(all_query_results)[:max_str_len]
    ai_message: AIMessage = queries["raw"]
    tool_call = queries["raw"].additional_kwargs["tool_calls"][0]
    tool_id = tool_call["id"]
    tool_message = ToolMessage(tool_call_id=tool_id, content=dumped)
    swapped_state["messages"].extend([ai_message, tool_message])
    generated = await gen_answer_chain.ainvoke(swapped_state)
    cited_urls = set(generated["parsed"].cited_urls)
    cited_references = {k: v for k, v in all_query_results.items() if k in cited_urls}
    formatted_message = AIMessage(name=name, content=generated["parsed"].as_str)
    return {"messages": [formatted_message], "references": cited_references}
