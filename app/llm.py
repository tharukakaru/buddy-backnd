import httpx
from openai import OpenAI

from app.config import settings


SYSTEM_PROMPT = (
    "You are Buddy AI, a helpful education assistant. "
    "Answer the user's question using only the provided context. "
    "If the answer is not in the context, say you do not have enough information. "
    "If the user asks in Sinhala, answer in Sinhala. "
    "If the user asks in English, answer in English. "
    "Keep the answer simple, clear, and student-friendly."
)


def build_user_prompt(question: str, context: str) -> str:
    """
    Build the RAG prompt sent to the answer-generation model.
    """
    return (
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        "Answer:"
    )


def generate_answer_with_deepseek(question: str, context: str) -> str:
    """
    Generate an answer using DeepSeek chat API.

    The retrieved context comes from Qdrant.
    The model should answer only using that context.
    """
    if not settings.deepseek_api_key:
        return (
            "DeepSeek API key is missing. "
            "Please add DEEPSEEK_API_KEY to the .env file."
        )

    url = f"{settings.deepseek_base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_user_prompt(
                    question=question,
                    context=context,
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

    try:
        response = httpx.post(
            url,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except httpx.HTTPStatusError as error:
        return f"DeepSeek API HTTP error: {error.response.status_code} - {error.response.text}"

    except Exception as error:
        return f"DeepSeek API request failed: {error}"


def generate_answer_with_openai(question: str, context: str) -> str:
    """
    Generate an answer using OpenAI chat completion.

    The retrieved context comes from Qdrant.
    The model should answer only using that context.
    """
    if not settings.openai_api_key:
        return (
            "OpenAI API key is missing. "
            "Please add OPENAI_API_KEY to the .env file."
        )

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": build_user_prompt(
                        question=question,
                        context=context,
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=500,
        )

        return response.choices[0].message.content

    except Exception as error:
        return f"OpenAI API request failed: {error}"


def generate_answer(question: str, context: str) -> str:
    """
    Generate an answer using the configured LLM provider.

    .env options:
    - LLM_PROVIDER=openai
    - LLM_PROVIDER=deepseek
    """
    llm_provider = getattr(settings, "llm_provider", "deepseek")

    if llm_provider == "openai":
        return generate_answer_with_openai(
            question=question,
            context=context,
        )

    return generate_answer_with_deepseek(
        question=question,
        context=context,
    )
    