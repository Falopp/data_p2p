import os
import matplotlib.pyplot as plt
import seaborn as sns


def set_default_style(style: str = "whitegrid") -> None:
    """
    Aplica un estilo por defecto a todos los gráficos.

    Args:
        style: Nombre del estilo de Seaborn.
    """
    sns.set_theme(style=style)


def create_figure(
    figsize: tuple[float, float] = (12, 8)
) -> tuple[plt.Figure, plt.Axes]:
    """
    Crea una figura y ejes con el estilo por defecto.

    Args:
        figsize: Tamaño de la figura (anchura, altura) en pulgadas.

    Returns:
        fig, ax  # Objeto Figure y Axes de Matplotlib
    """
    set_default_style()
    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax


def save_figure(
    fig: plt.Figure,
    out_dir: str,
    filename: str,
    dpi: int = 300,
    tight_layout: bool = True,
    export_svg_pdf: bool = True,
) -> str:
    """
    Guarda una figura en disco, creando el directorio si hace falta.

    Args:
        fig: Objeto Figure de Matplotlib.
        out_dir: Directorio donde guardar.
        filename: Nombre de archivo (con extensión, e.g. 'grafico.png').
        dpi: Resolución en puntos por pulgada.
        tight_layout: Si aplicar tight_layout antes de guardar.

    Returns:
        Ruta absoluta al archivo guardado.
    """
    os.makedirs(out_dir, exist_ok=True)
    if tight_layout:
        try:
            fig.tight_layout()
        except Exception:
            pass
    file_path = os.path.join(out_dir, filename)
    fig.savefig(file_path, dpi=dpi, bbox_inches="tight")
    # Exportaciones adicionales para presentaciones de alta calidad
    if export_svg_pdf:
        base, _ = os.path.splitext(file_path)
        try:
            fig.savefig(f"{base}.svg", bbox_inches="tight")
        except Exception:
            pass
        try:
            fig.savefig(f"{base}.pdf", bbox_inches="tight")
        except Exception:
            pass
    plt.close(fig)
    return file_path
