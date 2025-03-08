from learnsys.models import FactorInterpretation

def interpret_educational_guidance(factor_results):
    """
    Интерпретирует образовательные рекомендации на основе результатов психологических тестов.
    :param factor_results: dict {factor_code: result_value}
    :return: dict {factor_code: {'factor_name': str, 'teacher_support': str, 'feedback': str, 'community': str}}
    """

    guidance_map = {
        "A1": [  # Мотивация
            (0, 7, "мотивация на неудачу", 3, 3, 3),
            (8, 9, "тенденция на неудачу", 2, 3, 3),
            (10, 11, "не выражен", 3, 2, 2),
            (12, 13, "тенденция на успех", 2, 1, 2),
            (14, 20, "мотивация на успех", 1, 2, 1),
        ],
        "A2": [  # Экстраверсия
            (0, 12, "интроверт", 2, 1, 1),
            (13, 24, "экстраверт", 3, 2, 3),
        ],
        "A3": [  # Нейротизм
            (0, 6, "низкий", 2, 1, 1),
            (7, 13, "средний", 3, 2, 2),
            (14, 18, "высокий", 3, 2, 3),
            (19, 24, "очень высокий", 3, 3, 1),
        ],
        "A4": [  # Темперамент
            (1, 1, "флегматик", 2, 1, 1),
            (2, 2, "сангвинник", 3, 3, 3),
            (3, 3, "меланхолик", 2, 2, 1),
            (4, 4, "холерик", 2, 1, 2),
        ],
    }

    recommendations = {}

    for factor_code, result_value in factor_results.items():
        if factor_code in guidance_map:
            for min_val, max_val, level_name, teacher_support, feedback, community in guidance_map[factor_code]:
                if min_val <= result_value <= max_val:
                    recommendations[factor_code] = {
                        "factor_name": FactorInterpretation.objects.filter(factor_code=factor_code).first().factor_name or "Неизвестно",
                        "teacher_support": get_teacher_support(teacher_support),
                        "feedback": get_feedback(feedback),
                        "community": get_community(community),
                    }
                    break  # Найдено соответствие, выходим из цикла

    return recommendations

def get_teacher_support(level):
    """Функция возвращает текстовое описание уровня помощи преподавателя."""
    mapping = {
        1: "Помощь преподавателя не требуется",
        2: "Рекомендуется обратиться за помощью к преподавателю",
        3: "Крайне необходимо вмешательство преподавателя",
    }
    return mapping.get(level, "Неизвестно")

def get_feedback(level):
    """Функция возвращает текстовое описание уровня обратной связи."""
    mapping = {
        1: "Обратная связь не нужна",
        2: "Рекомендуется связаться с преподавателем",
        3: "Настоятельно рекомендуется отчитаться преподавателю о своих результатах",
    }
    return mapping.get(level, "Неизвестно")

def get_community(level):
    """Функция возвращает текстовое описание уровня вовлеченности в комьюнити."""
    mapping = {
        1: "Вы справляетесь самостоятельно",
        2: "Рассмотрите возможность посещения различных мероприятий",
        3: "Настоятельно рекомендуется выход в люди",
    }
    return mapping.get(level, "Неизвестно")
