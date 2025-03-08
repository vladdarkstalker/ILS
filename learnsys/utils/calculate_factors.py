from collections import defaultdict
from ..models import PsychQuestion, PsychAnswer


def calculate_factors(user_answers, test, target_factors):
    # Функция получения суммы баллов для фактора
    def get_factor_score(factor):
        """Суммирует баллы по указанному фактору."""
        return sum(
            PsychAnswer.objects.get(id=answer_id).score
            for question_id, answer_id in user_answers.items()
            if PsychQuestion.objects.get(id=question_id).factor == factor
        )

    results = {}
    # Здесь добавьте расчёт для каждого фактора по формулам
    # results['F1'] = ((38 + 2 * get_factor_score('L') + 3 * get_factor_score('O') + 4 * get_factor_score('Q4')) -
    #                 2 * (get_factor_score('C') + get_factor_score('H') + get_factor_score('Q3'))) / 10
    # results['F2'] = ((2 * get_factor_score('A') + 3 * get_factor_score('E') + 4 * get_factor_score('F') + 5 * get_factor_score('H')) -
    #                 (2 * get_factor_score('Q2') + 11)) / 10
    # results['F3'] = ((77 + 2 * get_factor_score('C') + 2 * get_factor_score('E') + 2 * get_factor_score('F') + 2 * get_factor_score('N')) -
    #                 (4 * get_factor_score('A') + 6 * get_factor_score('I') + 2 * get_factor_score('M'))) / 10
    # results['F4'] = ((4 * get_factor_score('E') + 3 * get_factor_score('M') + 4 * get_factor_score('Q1') + 4 * get_factor_score('Q2')) -
    #                 (3 * get_factor_score('A') + 2 * get_factor_score('G'))) / 10

    # Рассчитываем базовые факторы
    all_factors = PsychQuestion.objects.filter(test=test).values_list('factor', flat=True).distinct()
    for factor in all_factors:
        results[factor] = get_factor_score(factor)

    # Пример добавления формул для расчетных факторов
    if 'A2' in results and 'A3' in results:
        results['A4'] = (
            1 if results['A3'] < 12 and results['A2'] < 12 else
            2 if results['A3'] < 12 and results['A2'] > 12 else
            3 if results['A3'] > 12 and results['A2'] < 12 else
            4 if results['A3'] > 12 and results['A2'] > 12 else
            0
        )
        # Фильтруем результаты, исключая значения 0 или None
    filtered_results = {
        factor: value for factor, value in results.items()
        if value not in (0, None)
    }
    return filtered_results
