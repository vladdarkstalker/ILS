# generate_questions.py
from django.core.management.base import BaseCommand
from django.conf import settings
from learnsys.models import Topic, Test, TestItem
from haystack.nodes import QuestionGenerator, FARMReader, TransformersTranslator
from haystack.pipelines import QuestionAnswerGenerationPipeline, TranslationWrapperPipeline
from haystack.document_stores import InMemoryDocumentStore
from tqdm.auto import tqdm
import logging

class Command(BaseCommand):
    help = 'Генерирует вопросы на основе текстов тем'

    def handle(self, *args, **options):
        topics = Topic.objects.all()

        for topic in topics:
            generate_questions_for_topic(topic)
            self.stdout.write(f"Вопросы для темы '{topic.name}' сгенерированы.")
            
