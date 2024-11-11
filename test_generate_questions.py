# test_generate_questions.py

from learnsys.utils.question_generation import generate_questions_from_text

def test_generate_questions():
    sample_text = (
        "Artificial intelligence is intelligence demonstrated by machines, unlike the natural intelligence displayed by humans and animals. "
        "Leading AI textbooks define the field as the study of 'intelligent agents': any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals."
    )
    questions_and_answers = generate_questions_from_text(sample_text)
    print(questions_and_answers)

if __name__ == "__main__":
    test_generate_questions()
