from learnsys.models import FactorInterpretation
def get_teacher_support(level):
    """Возвращает текстовое описание уровня помощи преподавателя."""
    mapping = {
        1: "Помощь преподавателя не требуется",
        2: "Рекомендуется обратиться за помощью к преподавателю",
        3: "Крайне необходимо вмешательство преподавателя",
    }
    return mapping.get(level, "Неизвестно")

def get_feedback(level):
    """Возвращает текстовое описание уровня обратной связи."""
    mapping = {
        1: "Обратная связь не нужна",
        2: "Вам будет интересно показать свою работу преподавателю",
        3: "Обсудите свой прогресс с преподавателями, это точно принесет вам положительный результат",
    }
    return mapping.get(level, "Неизвестно")

def get_community(level):
    """Возвращает текстовое описание уровня вовлеченности в комьюнити."""
    mapping = {
        1: "Вы справляетесь самостоятельно",
        2: "Рассмотрите возможность обсудить ваше обучение с однокурсниками",
        3: "Вам рекомендуется больше проводить времени на мозговых штурмах с вашими коллегами по учебе",
    }
    return mapping.get(level, "Неизвестно")

def interpret_educational_guidance(guidance_results):
    """
    Интерпретирует образовательные рекомендации.
    :param guidance_results: dict {factor_code+T/R/C: numeric_value}
    :return: dict {factor_code: {'factor_name': str, 'T': str, 'R': str, 'C': str}}
    """
    recommendations = {}

    # Проход по всем рекомендациям
    for factor_code_with_suffix, value in guidance_results.items():
        base_factor = factor_code_with_suffix[:-1]  # A1 из A1T
        recommendation_type = factor_code_with_suffix[-1]  # T, R, C

        if base_factor not in recommendations:
            recommendations[base_factor] = {
                "factor_name": FactorInterpretation.objects.filter(factor_code=base_factor).first().factor_name or "Неизвестно",
                "T": "Нет данных", "R": "Нет данных", "C": "Нет данных"
            }

        # Преобразуем числовое значение рекомендации в текст
        if recommendation_type == "T":
            recommendations[base_factor]["T"] = get_teacher_support(value)
        elif recommendation_type == "R":
            recommendations[base_factor]["R"] = get_feedback(value)
        elif recommendation_type == "C":
            recommendations[base_factor]["C"] = get_community(value)

    return recommendations

