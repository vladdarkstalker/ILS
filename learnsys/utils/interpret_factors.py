from ..models import FactorInterpretation
def interpret_factors(results):
    interpretations = {}
    for result in results:
        factor = FactorInterpretation.objects.filter(factor_code=result.factor).first()
        if factor:
            interpretation_text = factor.get_interpretation(result.result)
            interpretations[result.factor] = {
                "name": factor.factor_name,
                "value": interpretation_text
            }
        else:
            interpretations[result.factor] = {
                "name": "Неизвестный фактор",
                "value": "Неизвестное значение"
            }
    return interpretations

