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
    selected_layer = st.selectbox(' ', layers)

    # Filtrar el GeoDataFrame por la capa seleccionada
    filtered_gdf = gdf[gdf['Layer'] == selected_layer]

    return filtered_gdf

