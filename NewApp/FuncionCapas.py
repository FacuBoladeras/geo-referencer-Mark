import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import io
from PIL import Image
from shapely.ops import polygonize
import json

pre_selected_layers = ['70-spaces', 'A-ROOMS','A-Areas','A-AREAS','Workplaces','_MKD_ROOM']

def select_and_visualize_layers(gdf, key_suffix=""):
    # Obtener las capas únicas del GeoDataFrame
    layers = gdf['Layer'].unique()
    
    # Seleccionar una capa usando un widget de selección
    # selected_layer = st.selectbox('Select layer:', layers, key=f"selectbox_{key_suffix}")

    # add multi layer selection
    def_select = [layer for layer in layers if layer in pre_selected_layers]

    selected_layer = st.multiselect('Select layers:', layers, default=def_select ,key=f"multiselect_{key_suffix}")

    # Filtrar el GeoDataFrame por la capa seleccionada
    filtered_gdf = gdf[gdf['Layer'].isin(selected_layer)]

    return filtered_gdf


