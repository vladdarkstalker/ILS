import whisper
from transformers import MarianMTModel, MarianTokenizer
import tempfile
import os
import subprocess
import logging
import torch
from pydub import AudioSegment
import nltk
from nltk.tokenize.punkt import PunktSentenceTokenizer
from nltk import download

logger = logging.getLogger(__name__)

WHISPER_MODEL = None
TRANSLATOR_MODEL = None
TRANSLATOR_TOKENIZER = None

def get_directml_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")

def get_whisper_model():
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        device = torch.device("cpu")
        WHISPER_MODEL = whisper.load_model("small").to(device)
        logger.info(f"Whisper модель загружена на устройство: {device}")
    return WHISPER_MODEL

def transcribe_single_chunk(chunk_path):
    model = get_whisper_model()
    result = model.transcribe(chunk_path, language=None)
    return result.get('text', '').strip()

def transcribe_audio(file_path):
    chunks = split_audio(file_path)
    full_transcription = ""
    for chunk in chunks:
        try:
            transcription = transcribe_single_chunk(chunk)
            full_transcription += transcription + " "
        except Exception as e:
            logger.error(f"Ошибка при транскрипции части {chunk}: {e}", exc_info=True)
        finally:
            if os.path.exists(chunk):
                os.remove(chunk)
    return full_transcription

def extract_audio(video_path):
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
        temp_audio_name = temp_audio.name
    command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', temp_audio_name, '-y']
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return temp_audio_name

def get_translator():
    global TRANSLATOR_MODEL, TRANSLATOR_TOKENIZER
    if TRANSLATOR_MODEL is None or TRANSLATOR_TOKENIZER is None:
        model_name = 'Helsinki-NLP/opus-mt-ru-en'
        TRANSLATOR_TOKENIZER = MarianTokenizer.from_pretrained(model_name)
        TRANSLATOR_MODEL = MarianMTModel.from_pretrained(model_name)
        device = get_directml_device()
        TRANSLATOR_MODEL.to(device)
        logger.info(f"Мариянская модель перевода загружена на устройство: {device}")
    return TRANSLATOR_MODEL, TRANSLATOR_TOKENIZER

def translate_ru_to_en(text):
    model, tokenizer = get_translator()

    download('punkt', quiet=True)
    nltk.data.path.append("/home/vladdarkstalker/nltk_data")
    sentence_tokenizer = PunktSentenceTokenizer()
    sentences = sentence_tokenizer.tokenize(text)

    translated_sentences = []
    for sentence in sentences:
        inputs = tokenizer(sentence, return_tensors="pt", padding=True, truncation=True, max_length=512)
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        translated = model.generate(**inputs)
        translated_sentence = tokenizer.decode(translated[0], skip_special_tokens=True)
        translated_sentences.append(translated_sentence)

    return ' '.join(translated_sentences)

def split_audio(file_path, chunk_length_ms=60000):
    audio = AudioSegment.from_file(file_path)
    chunks = []
    for i in range(0, len(audio), chunk_length_ms):
        chunk = audio[i:i + chunk_length_ms]
        chunk_filename = f"{file_path}_chunk_{i // chunk_length_ms}.mp3"
        chunk.export(chunk_filename, format="mp3")
        chunks.append(chunk_filename)
    return chunks

def process_content(content_instance):
    content_type = content_instance.content_type
    if content_type in ['audio', 'video']:
        file_path = content_instance.content.path
        try:
            transcribed_text = transcribe_audio(file_path)
            logger.debug(f"Распознанный текст: {transcribed_text[:100]}...")
            from langdetect import detect
            detected_language = detect(transcribed_text)
            logger.debug(f"Определён язык аудио: {detected_language}")
            translated_text = (
                translate_ru_to_en(transcribed_text) if detected_language == 'ru' else transcribed_text
            )
            content_instance.generated_text = translated_text
            content_instance.save()
            logger.debug(f"Контент ID {content_instance.id} успешно обработан.")
            return True, "Контент успешно обработан."
        except Exception as e:
            logger.error(f"Ошибка при обработке контента ID {content_instance.id}: {e}", exc_info=True)
            return False, f"Ошибка при обработке файла: {e}"
    elif content_type == 'text':
        try:
            from langdetect import detect
            language = detect(content_instance.text_content)
            logger.debug(f"Определён язык текста: {language}")
            translated_text = (
                translate_ru_to_en(content_instance.text_content) if language == 'ru' else content_instance.text_content
            )
            content_instance.generated_text = translated_text
            content_instance.save()
            logger.debug(f"Текстовый контент ID {content_instance.id} успешно обработан.")
            return True, "Текстовый контент успешно обработан."
        except Exception as e:
            logger.error(f"Ошибка при обработке контента ID {content_instance.id}: {e}", exc_info=True)
            return False, f"Ошибка при обработке текста: {e}"
    else:
        return False, "Тип контента не поддерживается для обработки."