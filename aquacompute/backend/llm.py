import os
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load .env from backend folder or current working directory
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv()

# Tier to model mapping constants (matched to models available on this Groq account)
TIER_MODELS = {
    "small": {"name": "GPT OSS 20B", "id": "openai/gpt-oss-20b"},
    "medium": {"name": "Qwen 3.8 27B", "id": "qwen/qwen3.8-27b"},
    "large": {"name": "GPT OSS 120B", "id": "openai/gpt-oss-120b"},
}

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def ask(prompt: str, model_id: str) -> dict:
    """Send a prompt to Groq via the OpenAI SDK and return the cleaned reply and token usage."""
    api_key = os.getenv("GROQ_API_KEY")
    client = OpenAI(base_url=GROQ_BASE_URL, api_key=api_key or "missing")
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        raise RuntimeError(f"Groq API call failed: {exc}") from exc

    raw_text = response.choices[0].message.content or ""
    cleaned_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

    usage = response.usage
    input_tokens = usage.prompt_tokens if usage else 0
    output_tokens = usage.completion_tokens if usage else 0

    return {
        "text": cleaned_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
