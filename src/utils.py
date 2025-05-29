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

def sanitize_filename_component(filename_part: str) -> str:
    """Reemplaza caracteres no válidos en un componente de nombre de archivo con guiones bajos."""
    if not isinstance(filename_part, str):
        filename_part = str(filename_part)
    
    # Caracteres comunes no permitidos o problemáticos en nombres de archivo en varios OS
    # Se omiten / y \ ya que os.path.join los maneja, pero es bueno ser precavido.
    # Espacios se reemplazan para evitar problemas en algunos contextos.
    invalid_chars = r'<>:"/\|?* '
    sanitized = filename_part
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Reducir múltiples guiones bajos a uno solo
    while '__' in sanitized:
        sanitized = sanitized.replace('__', '_')
        
    # Eliminar guiones bajos al principio o al final si los hay
    sanitized = sanitized.strip('_')
    
    # Limitar longitud por si acaso (algunos sistemas tienen límites bajos)
    # Un límite razonable podría ser 50-60 chars para un componente.
    max_len = 50 
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len]
        # Si se cortó y termina en _, quitarlo
        sanitized = sanitized.strip('_')
        
    if not sanitized: # Si después de todo queda vacío, poner un placeholder
        return "default_name"
        
    return sanitized 

def format_large_number(num: float | int, use_decimal_separator: bool = True, precision: int = 1) -> str:
    """
    Formatea números grandes a una representación más legible (K, M, B, T).
    Ej: 1234 -> 1.2K, 1234567 -> 1.2M
    """
    if num is None:
        return "N/A"
    if abs(num) < 1000:
        if isinstance(num, int):
            return str(num)
        else:
            # Para números menores a 1000 pero con decimales, controlar la precisión
            return f"{num:.{precision}f}" if num % 1 != 0 else str(int(num))


    suffixes = ['', 'K', 'M', 'B', 'T']  # Kilo, Mega, Giga (Billions), Tera
    magnitude = 0
    # Determinar la magnitud mientras el número sea >= 1000
    # y no hayamos llegado al final de nuestra lista de sufijos
    temp_num = abs(num)
    while temp_num >= 1000 and magnitude < len(suffixes) - 1:
        temp_num /= 1000.0
        magnitude += 1
    
    # Aplicar el formato
    # Usar el signo del número original
    formatted_num_val = num / (1000.0 ** magnitude)
    
    # Formatear con la precisión deseada
    # Si el número es esencialmente un entero después de la escala, no mostrar decimales innecesarios
    if formatted_num_val % 1 == 0:
        base_formatted = str(int(formatted_num_val))
    else:
        base_formatted = f"{formatted_num_val:.{precision}f}"

    return f"{base_formatted}{suffixes[magnitude]}" 