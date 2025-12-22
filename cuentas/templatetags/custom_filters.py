from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """
    Divide el valor por el argumento.
    Uso en template: {{ valor|div:argumento }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    """
    Multiplica el valor por el argumento.
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract(value, arg):
    """
    Resta el argumento del valor.
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def add(value, arg):
    """
    Suma el argumento al valor.
    """
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def percentage(value, total):
    """
    Calcula el porcentaje que representa value de total.
    Uso: {{ valor|percentage:total }}
    """
    try:
        if total == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0

@register.filter
def format_currency(value):
    """
    Formatea un número como moneda.
    """
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return f"$0.00"

@register.filter
def filter_by_materia(queryset, materia_id):
    """
    Filtra un queryset por materia_id.
    NOTA: Este filtro puede no funcionar directamente en templates
    porque los querysets en contexto no son los mismos objetos.
    Mejor calcular estos datos en la vista.
    """
    # Esta función es más compleja de implementar en un filtro simple
    # Te recomiendo calcular esto en la vista directamente
    return queryset.filter(materia_id=materia_id) if hasattr(queryset, 'filter') else queryset

@register.simple_tag
def calcular_promedio_clase(monto_total, num_clases):
    """
    Tag para calcular promedio por clase.
    Uso: {% calcular_promedio_clase monto_total num_clases %}
    """
    try:
        if num_clases == 0:
            return 0
        return round(float(monto_total) / float(num_clases), 2)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(dictionary, key):
    """
    Obtiene un valor de un diccionario por clave.
    Uso: {{ dict|get_item:key }}
    """
    return dictionary.get(key, '')