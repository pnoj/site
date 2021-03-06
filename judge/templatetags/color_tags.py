from django import template
from django.utils.safestring import mark_safe
from django.shortcuts import reverse
from judge import models
 
register = template.Library()
 
@register.filter
def status_color(status):
    status_colors = {
        'ac': 'success',
        'wa': 'danger',
        'tle': 'info',
        'mle': 'info',
        'ole': 'info',
        'ir': 'warning',
        'ce': 'secondary',
        'g': 'light',
        'ie': 'secondary',
        'md': 'light',
        'ab': 'secondary',
    }
    return status_colors[status.lower()]

@register.filter
def problem_color(problem, user):
    if user.has_attempted(problem):
        if user.has_solved(problem):
            return "success"
        else:
            return "warning"
    else:
        return "light"
