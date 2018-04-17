from django import template

register = template.Library()


@register.simple_tag
def response_icon(status):
    icons = {
        "S": "fa-envelope",
        "V": "fa-check",
        "I": "fa-trash"
    }
    return icons.get(status, "fa-question")
