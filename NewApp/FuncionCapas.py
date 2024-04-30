import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import io
from PIL import Image
from shapely.ops import polygonize
import json

def select_and_visualize_layers(gdf):
    # Obtener las capas únicas del GeoDataFrame
    layers = gdf['Layer'].unique()
    
    # Seleccionar una capa usando un widget de selección
    selected_layer = st.selectbox('Selecciona una capa:', layers)

    # Filtrar el GeoDataFrame por la capa seleccionada
    filtered_gdf = gdf[gdf['Layer'] == selected_layer]

    # Visualizar las geometrías filtradas en un gráfico
    fig, ax = plt.subplots(figsize=(7, 7))
    filtered_gdf.plot(ax=ax, color='blue', alpha=0.5, edgecolor='k', linewidth=0.5)
    plt.axis('off')

    # Convertir el gráfico a una imagen para mostrar en Streamlit
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img = Image.open(buf)

    # Mostrar la imagen en Streamlit
    st.image(img, output_format='PNG', use_column_width=False)

    # Cerrar la figura de matplotlib para liberar memoria
    plt.close(fig)

    return filtered_gdf

