import logging
import re
import json
import requests
from .llm_generation import call_local_mistral

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE_SINGLE_ANSWER = """
Вы — генератор тестовых вопросов. По приведённому тексту составьте вопрос с одним верным ответом и тремя отвлекающими.
Верни строго JSON:
[
    {{
        "question": "текст вопроса",
        "answer": "правильный ответ",
        "distractors": ["отвлекающий 1", "отвлекающий 2", "отвлекающий 3"]
    }}
]
Текст: {text}
"""

PROMPT_TEMPLATE_MULTI_ANSWER = """
Вы — генератор тестовых вопросов. По приведённому тексту составьте вопрос с несколькими правильными ответами и тремя отвлекающими.
Верни строго JSON:
[
    {{
        "question": "текст вопроса",
        "answers": ["правильный ответ 1", "правильный ответ 2"],
        "distractors": ["отвлекающий 1", "отвлекающий 2", "отвлекающий 3"]
    }}
]
Текст: {text}
"""

PROMPT_TEMPLATE_SINGLE = """
Вы — генератор тестовых вопросов. По приведённому тексту составьте один вопрос с одним верным ответом и тремя отвлекающими.
Верни строго JSON:
{{
    "question": "текст вопроса",
    "answer": "правильный ответ",
    "distractors": ["отвлекающий 1", "отвлекающий 2", "отвлекающий 3"]
}}
Текст: {text}
"""

PROMPT_TEMPLATE_MULTIPLE = """
Вы — генератор тестовых вопросов. По приведённому тексту составьте один вопрос с несколькими правильными ответами (2-3) и тремя отвлекающими.
Верни строго JSON:
{{
    "question": "текст вопроса",
    "answers": ["правильный ответ 1", "правильный ответ 2"],
    "distractors": ["отвлекающий 1", "отвлекающий 2", "отвлекающий 3"]
}}
Текст: {text}
"""

PROMPT_TEMPLATE = """
Вы — генератор тестовых вопросов. По приведённому тексту составьте от 1 до 3 вопросов в JSON-формате.

Каждый объект должен содержать:
- "question": текст вопроса.
- "answers": список правильных ответов (1 или несколько).
- "distractors": список из 2-3 отвлекающих ответов, связанных с темой.

Ответ верните в виде списка JSON. Никаких комментариев.

Текст:
{text}
"""

def parse_json_response(response_text):
    try:
        start = response_text.find('[')
        end = response_text.rfind(']') + 1
        if start == -1 or end == -1:
            logger.warning("Ответ не содержит JSON: %s", response_text)
            return None
        return json.loads(response_text[start:end])
    except json.JSONDecodeError as e:
        logger.error("Ошибка при парсинге JSON: %s | Текст: %s", e, response_text)
        return None

def call_local_mistral(prompt):
    try:
        response = requests.post('http://localhost:8080/completion', json={
            'prompt': prompt,
            'temperature': 0.7,
            'max_tokens': 512,
            'stop': ['###']
        }, timeout=60)
        response.raise_for_status()
        return response.json().get('content', '')
    except Exception as e:
        logger.error(f'Ошибка при вызове LLM: {e}')
        return ''

def parse_json_from_response(response_text):
    try:
        # Находим первый список в JSON формате
        json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
        if not json_match:
            logger.warning(f'JSON не найден в ответе: {response_text[:500]}')
            return None

        json_str = json_match.group(0)
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)  # Исправляем возможные отсутствующие кавычки
        json_str = json_str.replace("'", '"')  # Одинарные кавычки заменяем на двойные

        result = json.loads(json_str)

        # ВАЖНО: проверка что это список словарей, иначе ошибка
        if isinstance(result, list) and all(isinstance(i, dict) for i in result):
            return result
        else:
            logger.error(f'Ожидался список словарей, получено: {type(result)} — {result}')
            return None

    except json.JSONDecodeError as e:
        logger.error(f'Ошибка при парсинге JSON: {e} | Текст: {response_text[:500]}')
        return None

def generate_single_choice_questions(text, content_id=None):
    prompt = PROMPT_TEMPLATE_SINGLE.format(text=text)
    response = call_local_mistral(prompt)

    result = parse_json_response(response)
    if not result or not isinstance(result, dict):
        logger.warning("Некорректный ответ single choice: %s", response)
        return []

    question = result.get('question', '').strip()
    answer = result.get('answer', '').strip()
    distractors = result.get('distractors', [])

    if not question or not answer or not distractors:
        logger.warning("Неполный single choice: %s", result)
        return []

    return [{
        'question': question,
        'answer': answer,
        'distractors': distractors,
        'content_id': content_id
    }]

def generate_multiple_choice_questions(text, content_id=None):
    prompt = PROMPT_TEMPLATE_MULTIPLE.format(text=text)
    response = call_local_mistral(prompt)

    result = parse_json_response(response)
    if not result or not isinstance(result, dict):
        logger.warning("Некорректный ответ multiple choice: %s", response)
        return []

    question = result.get('question', '').strip()
    answers = result.get('answers', [])
    distractors = result.get('distractors', [])

    if not question or not answers or not distractors:
        logger.warning("Неполный multiple choice: %s", result)
        return []

    return [{
        'question': question,
        'answers': answers,
        'distractors': distractors,
        'content_id': content_id
    }]

def generate_questions_from_text(text, content_id=None):
    prompt = PROMPT_TEMPLATE.format(text=text)
    response = call_local_mistral(prompt)

    result = parse_json_response(response)
    if not result or not isinstance(result, list):
        logger.warning("Некорректный JSON-ответ: %s", response)
        return []

    questions = []
    for item in result:
        if not isinstance(item, dict):
            logger.warning("Пропуск некорректного item: %s", item)
            continue

        question = item.get('question', '').strip()
        answers = item.get('answers', [])
        distractors = item.get('distractors', [])

        if not question or not distractors:
            logger.warning("Неполный объект: %s", item)
            continue

        if isinstance(answers, list) and len(answers) > 1:
            questions.append({
                'question': question,
                'answers': answers,
                'distractors': distractors,
                'type': 'multiple_choice',
                'content_id': content_id
            })
        elif isinstance(answers, list) and len(answers) == 1:
            questions.append({
                'question': question,
                'answer': answers[0],
                'distractors': distractors,
                'type': 'single_choice',
                'content_id': content_id
            })
        else:
            logger.warning("Некорректные answers: %s", answers)

    return questions
