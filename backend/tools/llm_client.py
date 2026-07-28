"""
Shared OpenAI client factory.

Wraps AsyncOpenAI with LangSmith's tracing wrapper so every agent's LLM
calls show up in LangSmith with latency, token usage, and cost - without
switching agents off the raw OpenAI SDK. Tracing itself is controlled by
the LANGSMITH_TRACING / LANGCHAIN_TRACING_V2 env var; the wrapper is a
no-op when tracing isn't enabled.
"""
from openai import AsyncOpenAI
from langsmith.wrappers import wrap_openai


def get_openai_client(api_key: str) -> AsyncOpenAI:
    """Return an AsyncOpenAI client instrumented for LangSmith tracing."""
    return wrap_openai(AsyncOpenAI(api_key=api_key))
