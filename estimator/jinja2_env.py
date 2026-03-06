from jinja2 import Environment

def currency_filter(value):
    try:
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return str(value)

def number_filter(value):
    try:
        return f"{value:,.0f}"
    except (ValueError, TypeError):
        return str(value)

def environment(**options):
    env = Environment(**options)
    env.filters["currency"] = currency_filter
    env.filters["number"] = number_filter
    return env
