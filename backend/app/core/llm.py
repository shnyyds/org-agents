import os
from dotenv import load_dotenv

load_dotenv()


def get_llm(model: str = None, temperature: float = 0):
    """
    Returns an initialized LangChain ChatOpenAI instance configured for Qwen/DashScope.
    When LLM_BACKEND=openclaw and no OPENAI_API_KEY is set, returns None to avoid crash.
    """
    from app.utils.logger import public_service_logger as logger

    backend = os.getenv("LLM_BACKEND", "langchain").lower()
    api_key = os.getenv("OPENAI_API_KEY")

    if backend == "openclaw" and not api_key:
        logger.info("LLM Config: OpenClaw mode, skipping LangChain LLM init (no API key)")
        return None

    from langchain_openai import ChatOpenAI

    base_url = os.getenv("OPENAI_API_BASE")
    model_name = model or os.getenv("MODEL_NAME", "qwen-plus")

    logger.info(f"LLM Config: Model={model_name}, BaseURL={base_url}, KeyPrefix={api_key[:5] if api_key else 'None'}...")

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=temperature,
        streaming=True,
        timeout=30,
    )
