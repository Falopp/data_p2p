"""
Configuración específica para el sistema de reportes unificados.
"""

# Configuración de estructura unificada
UNIFIED_CONFIG = {
    # Estructura de directorios consolidada
    'directory_structure': {
        'figures': {
            'usd_analysis': 'Análisis USD/USDT consolidado',
            'uyu_analysis': 'Análisis UYU consolidado', 
            'comparative': 'Comparativos USD vs UYU',
            'general': 'Análisis general multi-moneda',
            'counterparty': 'Análisis de contrapartes',
            'sessions': 'Análisis de sesiones de trading'
        },
        'reports': 'Reportes HTML unificados',
        'data_exports': 'Exportaciones de datos consolidados'
    },
    
    # Configuración de gráficos optimizados
    'figure_settings': {
        'dpi': 300,
        'figsize_default': (12, 8),
        'figsize_large': (16, 12),
        'figsize_comparative': (16, 6),
        'max_subplot_cols': 2,
        'color_palette': {
            'usd': '#27ae60',  # Verde
            'uyu': '#3498db',  # Azul
            'general': '#e74c3c',  # Rojo
            'comparative': ['#27ae60', '#3498db'],
            'accent': '#f39c12'  # Naranja
        }
    },
    
    # Configuración de Excel consolidado
    'excel_settings': {
        'max_raw_rows': 10000,
        'sheet_names': {
            'summary': 'Resumen_Ejecutivo',
            'usd_data': 'Datos_USD',
            'uyu_data': 'Datos_UYU',
            'metrics': 'Métricas_Por_Periodo',
            'comparative': 'Análisis_Comparativo'
        },
        'format_options': {
            'number_format': '#,##0',
            'currency_format': '$#,##0.00',
            'percentage_format': '0.00%'
        }
    },
    
    # Configuración de HTML unificado
    'html_settings': {
        'title': 'Reporte P2P Consolidado',
        'theme_colors': {
            'primary': '#2c3e50',
            'secondary': '#3498db', 
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c'
        },
        'navigation_tabs': [
            {'id': 'comparative', 'title': 'Análisis Comparativo', 'icon': 'fas fa-balance-scale'},
            {'id': 'usd-analysis', 'title': 'Análisis USD/USDT', 'icon': 'fas fa-dollar-sign'},
            {'id': 'uyu-analysis', 'title': 'Análisis UYU', 'icon': 'fas fa-peso-sign'},
            {'id': 'general', 'title': 'Análisis General', 'icon': 'fas fa-chart-pie'},
            {'id': 'counterparty', 'title': 'Contrapartes', 'icon': 'fas fa-handshake'},
            {'id': 'sessions', 'title': 'Sesiones', 'icon': 'fas fa-clock'}
        ]
    },
    
    # Configuración de análisis consolidado
    'analysis_settings': {
        'consolidation_strategies': {
            'temporal': 'monthly',  # monthly, weekly, daily
            'volume_aggregation': 'sum',
            'price_aggregation': 'mean',
            'count_aggregation': 'sum'
        },
        'chart_types': {
            'temporal_evolution': True,
            'activity_heatmaps': True,
            'payment_methods': True,
            'volume_distributions': True,
            'price_analysis': True,
            'comparative_plots': True
        },
        'filter_settings': {
            'min_transactions_for_chart': 5,
            'top_n_payment_methods': 10,
            'outlier_detection': False
        }
    },
    
    # Configuración de métricas clave
    'metrics_config': {
        'summary_metrics': [
            'total_operations',
            'total_volume_usd', 
            'total_volume_uyu',
            'unique_counterparties',
            'avg_transaction_size',
            'periods_analyzed'
        ],
        'temporal_metrics': [
            'monthly_volume',
            'monthly_operations',
            'growth_rates',
            'seasonality_patterns'
        ],
        'comparative_metrics': [
            'usd_vs_uyu_volume_ratio',
            'currency_preference_trends',
            'cross_currency_correlations'
        ]
    },
    
    # Configuración de optimización
    'performance_settings': {
        'lazy_loading': True,
        'chunk_size': 10000,
        'parallel_processing': True,
        'cache_intermediate_results': True,
        'compression': {
            'figures': False,  # PNG ya está comprimido
            'excel': True,
            'csv_exports': True
        }
    }
}

# Mapeo de análisis a funciones específicas
ANALYSIS_FUNCTION_MAP = {
    'usd_analysis': [
        'temporal_evolution',
        'activity_heatmap', 
        'payment_methods',
        'volume_distribution',
        'price_analysis'
    ],
    'uyu_analysis': [
        'temporal_evolution',
        'activity_heatmap',
        'payment_methods', 
        'volume_distribution',
        'price_analysis'
    ],
    'comparative': [
        'volume_comparison',
        'operations_comparison',
        'payment_methods_comparison',
        'temporal_correlation'
    ],
    'general': [
        'status_distribution',
        'asset_evolution',
        'counterparty_summary',
        'period_overview'
    ],
    'counterparty': [
        'top_counterparties',
        'counterparty_networks',
        'trading_patterns',
        'loyalty_analysis'
    ],
    'sessions': [
        'session_length_analysis',
        'peak_hours',
        'day_of_week_patterns',
        'session_success_rates'
    ]
}

def get_unified_config():
    """Retorna la configuración unificada completa."""
    return UNIFIED_CONFIG

def get_analysis_functions(analysis_type: str):
    """Retorna las funciones de análisis para un tipo específico."""
    return ANALYSIS_FUNCTION_MAP.get(analysis_type, [])

def get_color_for_currency(currency: str):
    """Retorna el color asignado para una moneda específica."""
    colors = UNIFIED_CONFIG['figure_settings']['color_palette']
    return colors.get(currency.lower(), colors['general'])

def get_figure_size(chart_type: str):
    """Retorna el tamaño de figura apropiado para un tipo de gráfico."""
    settings = UNIFIED_CONFIG['figure_settings']
    
    if chart_type in ['comparative', 'side_by_side']:
        return settings['figsize_comparative']
    elif chart_type in ['detailed', 'multi_subplot']:
        return settings['figsize_large']
    else:
        return settings['figsize_default'] 