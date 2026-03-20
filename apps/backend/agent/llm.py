"""
LLM factory — returns the right LangChain chat model based on environment
variables, without touching any graph code.

Switching providers:
  LLM_PROVIDER=anthropic    → ChatAnthropic   (default, uses ANTHROPIC_API_KEY)
  LLM_PROVIDER=openrouter   → ChatOpenAI      (uses OPENROUTER_API_KEY, OpenAI-compat endpoint)
  LLM_PROVIDER=groq         → ChatOpenAI      (uses GROQ_API_KEY, OpenAI-compat endpoint)

The graph nodes call `get_llm()` then immediately call `.with_structured_output(schema)`
on the result.  This method is part of the LangChain BaseChatModel interface and is
supported by all three providers above.

Why LangChain models instead of the raw `anthropic` SDK?
  `.with_structured_output()` handles the tool-calling protocol differences between
  providers automatically.  Nodes never see provider-specific code.
"""
import os


def get_llm():
    """Return a LangChain chat model configured for the active provider."""
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    model = os.getenv("LLM_MODEL")

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model or "claude-sonnet-4-6",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    if provider == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "anthropic/claude-3.5-sonnet",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    if provider == "groq":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER={provider!r}. "
        "Valid options: 'anthropic', 'openrouter', 'groq'."
    )
