from collections import defaultdict
from ..models import PsychQuestion, PsychAnswer
def calculate_factors(user_answers, test):
    # Функция получения суммы баллов для фактора
    def get_factor_score(factor):
        return sum(
            PsychAnswer.objects.get(id=answer_id).score
            for question_id, answer_id in user_answers.items()
            if PsychQuestion.objects.get(id=question_id).factor == factor
        )

    results = {}
    # Здесь добавьте расчёт для каждого фактора по формулам
    results['F1'] = ((38 + 2 * get_factor_score('L') + 3 * get_factor_score('O') + 4 * get_factor_score('Q4')) -
                     2 * (get_factor_score('C') + get_factor_score('H') + get_factor_score('Q3'))) / 10
    results['F2'] = ((2 * get_factor_score('A') + 3 * get_factor_score('E') + 4 * get_factor_score('F') + 5 * get_factor_score('H')) -
                     (2 * get_factor_score('Q2') + 11)) / 10
    results['F3'] = ((77 + 2 * get_factor_score('C') + 2 * get_factor_score('E') + 2 * get_factor_score('F') + 2 * get_factor_score('N')) -
                     (4 * get_factor_score('A') + 6 * get_factor_score('I') + 2 * get_factor_score('M'))) / 10
    results['F4'] = ((4 * get_factor_score('E') + 3 * get_factor_score('M') + 4 * get_factor_score('Q1') + 4 * get_factor_score('Q2')) -
                     (3 * get_factor_score('A') + 2 * get_factor_score('G'))) / 10

    return results