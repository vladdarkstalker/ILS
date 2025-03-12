from ..models import PsychQuestion, PsychAnswer

def get_factor_score(user_answers, factor):
    return sum(
        PsychAnswer.objects.get(id=answer_id).score
        for question_id, answer_id in user_answers.items()
        if PsychQuestion.objects.get(id=question_id).factor == factor
    )

def calculate_factors(user_answers, test, target_factors):
    results = {}

    all_factors = PsychQuestion.objects.filter(test=test).values_list('factor', flat=True).distinct()
    for factor in all_factors:
        results[factor] = get_factor_score(user_answers, factor)

    if 'A2' in results and 'A3' in results:
        results['A4'] = (
            1 if results['A3'] < 12 and results['A2'] < 12 else
            2 if results['A3'] < 12 and results['A2'] >= 12 else
            3 if results['A3'] >= 12 and results['A2'] < 12 else
            4
        )

    interpretations = {
        'A1': [(0,7,3,3,3),(8,9,2,3,3),(10,11,3,2,2),(12,13,2,1,2),(14,20,1,2,1)],
        'A2': [(0,4,2,1,1),(5,8,2,1,1),(9,15,3,2,3),(16,19,3,2,3),(20,24,3,2,3)],
        'A3': [(0,6,2,1,1),(7,13,3,2,2),(14,18,3,2,3),(19,24,3,3,1)],
        'A4': [(1,1,2,1,1),(2,2,3,3,3),(3,3,2,2,1),(4,4,2,1,2)]
    }

    for factor, ranges in interpretations.items():
        if factor in results:
            factor_value = results[factor]
            for min_v, max_v, T, R, C in ranges:
                if min_v <= factor_value <= max_v:
                    results[f"{factor}T"] = T
                    results[f"{factor}R"] = R
                    results[f"{factor}C"] = C
                    break

    filtered_results = {factor: value for factor, value in results.items() if value not in (0, None)}

    return filtered_results
