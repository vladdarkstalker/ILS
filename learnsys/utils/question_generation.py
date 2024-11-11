# utils/question_generation.py

import logging
import traceback
from haystack.nodes import QuestionGenerator, FARMReader
from haystack.pipelines import QuestionAnswerGenerationPipeline
from haystack.document_stores import InMemoryDocumentStore
from haystack.schema import Answer

logger = logging.getLogger('learnsys')  # Убедитесь, что имя логгера соответствует настройкам

def generate_questions_from_text(text):
    logger.debug(f"Начало генерации вопросов для текста: {text[:100]}...")
    try:
        # Инициализация хранилища документов
        document_store = InMemoryDocumentStore()
        docs = [{"content": text}]
        document_store.write_documents(docs)

        # Инициализация генератора вопросов и Reader с указанием моделей
        question_generator = QuestionGenerator(model_name_or_path="valhalla/t5-small-qg-hl")  # Используйте рабочую модель
        reader = FARMReader(model_name_or_path="deepset/roberta-base-squad2")

        # Создание конвейера
        qag_pipeline = QuestionAnswerGenerationPipeline(question_generator, reader)

        # Генерация вопросов и ответов
        questions_and_answers = []
        for idx, document in enumerate(document_store.get_all_documents()):
            logger.info(f"Генерируем вопросы и ответы для документа {idx}")
            result = qag_pipeline.run(documents=[document])

            # Выводим результат для отладки
            logger.debug("Результат генерации:")
            logger.debug(result)

            # Извлекаем вопросы из 'queries' и ответы из 'answers'
            queries = result.get('queries', [])
            answers = result.get('answers', [])

            # Проверяем, что количество вопросов и ответов совпадает
            if len(queries) != len(answers):
                logger.error("Количество вопросов и ответов не совпадает")
                continue

            for question, answer_list in zip(queries, answers):
                # Берём первый ответ из списка ответов
                if answer_list:
                    first_answer = answer_list[0]
                    if isinstance(first_answer, Answer):
                        answer_text = first_answer.answer
                    else:
                        logger.warning(f"Неизвестный формат ответа: {type(first_answer)}")
                        answer_text = ''
                else:
                    answer_text = ''

                questions_and_answers.append({'question': question, 'answer': answer_text})

        logger.debug(f"Всего сгенерировано вопросов: {len(questions_and_answers)}")
        return questions_and_answers
    except Exception as e:
        error_message = traceback.format_exc()
        logger.error(f"Ошибка при генерации вопросов: {error_message}")
        raise e  # Повторно выбрасываем исключение
