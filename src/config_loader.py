import logging
import yaml  # Necesario para cargar desde archivo
import os  # Necesario para verificar si el archivo existe

logger = logging.getLogger(__name__)

# --- Configuración por Defecto ---
DEFAULT_CONFIG = {
    "column_mapping": {
        "order_number": "Order Number",
        "order_type": "Order Type",
        "asset_type": "Asset Type",
        "fiat_type": "Fiat Type",
        "total_price": "Total Price",
        "price": "Price",
        "quantity": "Quantity",
        "status": "Status",
        "match_time_utc": "Match time(UTC)",
        "payment_method": "Payment Method",
        "maker_fee": "Maker Fee",
        "taker_fee": "Taker Fee",
        "sale_value_reference_fiat": None,
    },
    "sell_operation": {"indicator_column": "order_type", "indicator_value": "SELL"},
    "reference_fiat_for_sales_summary": "USD",
    "html_report": {
        "include_tables_default": ["asset_stats", "fiat_stats"],
        "include_figures_default": ["hourly_operations"],
    },
}


# --- Funciones de Configuración ---
def load_config(config_path: str | None = None) -> dict:
    """
    Carga la configuración desde un archivo YAML si se proporciona la ruta.
    Si no se proporciona una ruta, o si el archivo no existe o hay un error al cargarlo,
    devuelve la configuración por defecto.
    """
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f)
            if loaded_config and isinstance(loaded_config, dict):
                logger.info(f"Configuración cargada exitosamente desde: {config_path}")
                # Aquí se podría añadir una lógica para fusionar con DEFAULT_CONFIG
                # si se desea que el archivo solo sobreescriba partes.
                # Por ahora, el archivo de config reemplaza completamente si es válido.
                return loaded_config
            else:
                logger.warning(
                    f"El archivo de configuración '{config_path}' está vacío o no es un diccionario válido. Usando configuración por defecto."
                )
        except yaml.YAMLError as e:
            logger.error(
                f"Error parseando el archivo de configuración YAML '{config_path}': {e}. Usando configuración por defecto."
            )
        except Exception as e:
            logger.error(
                f"Error inesperado cargando el archivo de configuración '{config_path}': {e}. Usando configuración por defecto."
            )
    elif config_path:
        logger.warning(
            f"Archivo de configuración no encontrado en '{config_path}'. Usando configuración por defecto."
        )

    logger.info(
        "Usando configuración por defecto del script (ya sea porque no se especificó archivo, no se encontró, o hubo error)."
    )
    return DEFAULT_CONFIG.copy()


def setup_logging(config: dict | None = None):
    """Configura el logging básico."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("matplotlib").setLevel(
        logging.WARNING
    )  # Silenciar logs de matplotlib
    logging.getLogger("PIL").setLevel(logging.WARNING)  # Silenciar logs de Pillow
    logger.info("Logging configurado.")
