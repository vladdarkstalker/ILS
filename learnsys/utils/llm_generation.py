import subprocess
import json
import textwrap
import requests
import logging

logger = logging.getLogger(__name__)

def call_local_mistral(prompt: str, timeout: int = 60) -> str:
    """
    Отправляет промпт к локальному серверу llama/mistral и возвращает ответ.
    """
    try:
        response = requests.post(
            "http://localhost:8080/completion",
            json={"prompt": prompt, "temperature": 0.7, "max_tokens": 512, "stop": ["###"]},
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and 'content' in data:
            return data['content']
        logger.error(f"Некорректный ответ от сервера: {data}")
        return ""
    except Exception as e:
        logger.error(f"Ошибка при обращении к llama-server: {e}")
        return ""

def ask_mistral(prompt: str) -> str:
    result = subprocess.run(["ollama", "run", "mistral"], input=prompt, capture_output=True, text=True)
    return result.stdout.strip()

def generate_questions_from_paragraph(text: str, max_questions=3):
    prompt = textwrap.dedent(f"""
    You are a teacher assistant generating questions from a short paragraph.
    You must return a list of 1-3 question objects in JSON format.

    Each object must contain:
    - "question": meaningful, context-specific question
    - "type": "text", "single_choice" or "multiple_choice"
    - "answer": concise and specific answer (max 20 words)
    - "distractors": (if applicable) 2-3 plausible but wrong options, related to the context

    Focus on clarity, relevance, and diversity.

    Text:
    {text}

    Return only valid JSON list. No explanations.
    """)

    raw = ask_mistral(prompt)
    try:
        start = raw.find('[')
        end = raw.rfind(']') + 1
        return json.loads(raw[start:end])
    except Exception as e:
        print("Ошибка парсинга LLM-ответа:", e)
        return []
