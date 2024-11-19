from django import template
import locale

# Registrar la librería de filtros
register = template.Library()

# Configurar el locale para Chile
try:
    locale.setlocale(locale.LC_ALL, 'es_CL.UTF-8')  # Chile
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')  # Usa el locale por defecto del sistema si falla

@register.filter
def multiply(value, arg):
    """
    Multiplica dos valores.
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0  # Retorna 0 si hay un error

@register.filter
def format_currency(value):
    """
    Formatea un valor como moneda chilena.
    """
    try:
        value = float(value)
        # Formatea el valor como moneda con símbolo CLP
        return locale.currency(value, symbol=True, grouping=True)
    except (ValueError, TypeError):
        return value  # Retorna el valor original si hay un error
