import logging

logger = logging.getLogger(__name__)

def parse_amount(val: str | float | int) -> float | None:
    """Convierte strings con puntos de miles a float. Devuelve None si no se puede convertir."""
    if val is None or (isinstance(val, float) and val != val): # val != val es para NaN en Polars/Pandas con Arrow
        return None
    
    original_val = val

    if not isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return None # Devolver None en caso de error para que Polars lo trate como nulo
    
    val = val.strip()
    if '.' in val and ',' in val and val.rfind('.') < val.rfind(','):
        val = val.replace('.', '').replace(',', '.')
    elif ',' in val and '.' in val and val.rfind(',') < val.rfind('.'):
        val = val.replace(',', '')
    elif ',' in val and '.' not in val:
        if val.count(',') == 1 and len(val.split(',')[-1]) <=2:
             val = val.replace(',', '.')
        else:
             val = val.replace(',', '') 
    elif '.' in val and ',' not in val:
        parts = val.split('.')
        if len(parts) > 2:
            integer_part = "".join(parts[:-1])
            decimal_part = parts[-1]
            val = f"{integer_part}.{decimal_part}"
    
    try:
        return float(val)
    except ValueError:
        return None 