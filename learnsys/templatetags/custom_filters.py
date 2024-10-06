# custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter(name='is_choice_type')
def is_choice_type(value):
    return value in ['single_choice', 'multiple_choice']
