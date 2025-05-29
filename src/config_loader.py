import logging

logger = logging.getLogger(__name__)

# --- Configuración por Defecto ---
DEFAULT_CONFIG = {
    'column_mapping': {
        'order_number': "Order Number",
        'order_type': "Order Type",
        'asset_type': "Asset Type",
        'fiat_type': "Fiat Type",
        'total_price': "Total Price",
        'price': "Price",
        'quantity': "Quantity",
        'status': "Status",
        'match_time_utc': "Match time(UTC)",
        'payment_method': "Payment Method",
        'maker_fee': "Maker Fee",
        'taker_fee': "Taker Fee",
        'sale_value_reference_fiat': None
    },
    'sell_operation': {
        'indicator_column': "order_type",
        'indicator_value': "SELL"
    },
    'reference_fiat_for_sales_summary': "USD",
    'html_report': {
        'include_tables_default': ["asset_stats", "fiat_stats"],
        'include_figures_default': ["hourly_operations"]
    }
}

# --- Funciones de Configuración ---
def load_config() -> dict:
    """Devuelve la configuración por defecto."""
    logger.info("Usando configuración por defecto del script.")
    return DEFAULT_CONFIG.copy()

def setup_logging(config: dict | None = None):
    """Configura el logging básico."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger("matplotlib").setLevel(logging.WARNING) # Silenciar logs de matplotlib
    logging.getLogger("PIL").setLevel(logging.WARNING)      # Silenciar logs de Pillow
    logger.info("Logging configurado.") 