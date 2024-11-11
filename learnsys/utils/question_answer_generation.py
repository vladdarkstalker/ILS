# learnsys/utils/question_answer_generation.py

from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    AutoModelForQuestionAnswering,
    pipeline
)
from googletrans import Translator
import nltk
import logging
import traceback

from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import DBSCAN
import numpy as np

logger = logging.getLogger(__name__)

# Инициализация переводчика
translator = Translator()

# Модель для генерации вопросов
tokenizer_qg = AutoTokenizer.from_pretrained("mrm8488/t5-base-finetuned-question-generation-ap")
model_qg = AutoModelForSeq2SeqLM.from_pretrained("mrm8488/t5-base-finetuned-question-generation-ap")

# Модель для вопросно-ответной системы
tokenizer_qa = AutoTokenizer.from_pretrained("deepset/roberta-base-squad2")
model_qa = AutoModelForQuestionAnswering.from_pretrained("deepset/roberta-base-squad2")
qa_pipeline = pipeline('question-answering', model=model_qa, tokenizer=tokenizer_qa)

# Модель для получения эмбеддингов предложений
embedding_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

def translate_text(text, src_lang='ru', dest_lang='en'):
    try:
        translation = translator.translate(text, src=src_lang, dest=dest_lang)
        return translation.text
    except Exception as e:
        logger.error(f"Ошибка при переводе текста: {e}")
        return text  # Возвращаем исходный текст в случае ошибки

def generate_questions_and_answers(text):
    logger.debug(f"Начало генерации вопросов и ответов для текста: {text[:100]}...")
    try:
        questions_and_answers = []
        nltk.download('punkt', quiet=True)

        # Определяем язык исходного текста
        from langdetect import detect
        language = detect(text)
        logger.debug(f"Определён язык текста: {language}")

        # Переводим текст на английский, если он не на английском
        if language != 'en':
            text_en = translate_text(text, src_lang=language, dest_lang='en')
        else:
            text_en = text

        # Разбиваем текст на предложения
        sentences_en = nltk.sent_tokenize(text_en, language='english')

        for sentence_en in sentences_en:
            # Подготавливаем вход для генерации вопроса
            input_text = f"answer: {sentence_en}  context: {text_en}"
            inputs = tokenizer_qg.encode(input_text, return_tensors='pt', max_length=512, truncation=True)

            # Генерируем вопрос
            outputs = model_qg.generate(
                inputs,
                max_length=64,
                num_beams=5,
                early_stopping=True
            )
            question_en = tokenizer_qg.decode(outputs[0], skip_special_tokens=True)
            question_en = question_en.replace("question:", "").strip()

            # Используем модель QA для получения ответа
            qa_input = {
                'question': question_en,
                'context': text_en
            }
            answer_en = qa_pipeline(qa_input)['answer']

            # Переводим вопрос и ответ обратно на исходный язык, если требуется
            if language != 'en':
                question = translate_text(question_en, src_lang='en', dest_lang=language)
                answer = translate_text(answer_en, src_lang='en', dest_lang=language)
            else:
                question = question_en
                answer = answer_en

            # Добавляем в список вопросов и ответов
            questions_and_answers.append({'question': question.strip(), 'answer': answer.strip()})

        # Удаляем похожие вопросы
        questions_and_answers = cluster_and_select_questions(questions_and_answers, eps=0.5, min_samples=1)

        logger.debug(f"Всего сгенерировано вопросов и ответов: {len(questions_and_answers)}")
        return questions_and_answers

    except Exception as e:
        error_message = traceback.format_exc()
        logger.error(f"Ошибка при генерации вопросов и ответов: {error_message}")
        raise e

def cluster_and_select_questions(questions_and_answers, eps=0.5, min_samples=1):
    # Извлекаем вопросы
    questions = [qa['question'] for qa in questions_and_answers]
    # Получаем эмбеддинги вопросов
    embeddings = embedding_model.encode(questions)
    # Кластеризация
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine').fit(embeddings)
    labels = clustering.labels_
    unique_questions_and_answers = []
    seen_clusters = set()
    for idx, label in enumerate(labels):
        if label not in seen_clusters:
            seen_clusters.add(label)
            unique_questions_and_answers.append(questions_and_answers[idx])
    return unique_questions_and_answers
