import base64
import io

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

# IMPORTANTE para rodar em servidores (Vercel/Docker):
# Define o backend do Matplotlib para 'Agg' (não interface gráfica)
matplotlib.use("Agg")
ALPHA = 1.0


def calculate_wet_bulb(temp, rh):
    return (
        temp * np.arctan(0.151977 * (rh + 8.313659) ** 0.5)
        + np.arctan(temp + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * (rh**1.5) * np.arctan(0.023101 * rh)
        - 4.686035
    )


def get_delta_t_image(current_temp=None, current_rh=None):
    # Configuração do gráfico (mesma lógica do código anterior)
    # Malha vai um pouco além dos limites para preencher todo o espaço
    temp_range = np.linspace(0, 52, 220)
    rh_range = np.linspace(8, 102, 220)
    T, RH = np.meshgrid(temp_range, rh_range)
    DeltaT = T - calculate_wet_bulb(T, RH)

    # Quadro quadrado, ajuste com box_aspect
    fig, ax = plt.subplots(figsize=(7, 7), dpi=90)
    levels = [0, 2, 8, 10, 20]
    line_levels = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
    fill_colors = ["#FFC825", "#2F963A", "#FFC825", "#F66139"]
    line_colors = [
        "#000000",  # 2 - preto
        "#000000",  # 4 - preto
        "#FF6B35",  # 6 - laranja
        "#1f78b4",  # 8 - azul
        "#000000",  # 10 - preto
        "#8B4513",  # 12 - marrom
        "#9b59b6",  # 14 - roxo
        "#5a6c7d",  # 16 - cinza azulado
        "#6B3410",  # 18 - marrom escuro
        "#000000",  # 20 - preto
    ]

    cmap = matplotlib.colors.ListedColormap(fill_colors)
    _norm = matplotlib.colors.BoundaryNorm(levels, cmap.N)

    # Preenchimento opaco (sem transparência)
    ax.contourf(T, RH, DeltaT, levels=levels, cmap=cmap, alpha=ALPHA, extend="both")
    lines = ax.contour(
        T, RH, DeltaT, levels=line_levels, colors=line_colors, linewidths=1.0
    )
    ax.clabel(lines, inline=True, fontsize=9, colors=line_colors)

    # Sem marcadores adicionais nas linhas de contorno

    # Se houver dados atuais, marca no gráfico
    if current_temp is not None and current_rh is not None:
        ax.plot(
            current_temp,
            current_rh,
            marker="o",
            markersize=10,
            color="white",
            markeredgecolor="black",
            markeredgewidth=2,
        )

    ax.set_xlim(0, 50)
    ax.set_ylim(10, 100)
    ax.set_box_aspect(1)  # força a área do gráfico a ser quadrada
    ax.set_xticks(np.arange(0, 55, 5))
    ax.set_yticks(np.arange(10, 110, 10))
    ax.set_title("Condição de Pulverização - Delta T", fontsize=14, fontweight="bold")
    ax.set_xlabel("Temperatura °C", fontsize=12)
    ax.set_ylabel("Umidade Relativa %", fontsize=12)
    ax.tick_params(axis="both", which="both", labelsize=11, width=1.6, length=6)
    for spine in ax.spines.values():
        spine.set_linewidth(2)
        spine.set_color("#000")
    ax.grid(
        True, which="both", linestyle="solid", linewidth=1, color="#000000", alpha=ALPHA
    )

    # Sem marcadores na legenda: apenas linhas
    legend_handles = [
        Line2D(
            [0],
            [0],
            color=line_colors[i],
            linewidth=2,
            marker=None,
            label=f"{lvl}",
        )
        for i, lvl in enumerate(line_levels)
    ]
    ax.legend(
        handles=legend_handles,
        title="Delta T",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=True,
        edgecolor="#ccc",
        framealpha=ALPHA,
        fontsize=10,
        title_fontsize=11,
    )

    buf = io.BytesIO()

    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)  # Importante para liberar memória
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return data
