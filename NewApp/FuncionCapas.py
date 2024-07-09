import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import io
from PIL import Image
from shapely.ops import polygonize
import json

floor_layers = ['70-spaces','A-Areas','A-AREAS',]
room_layers = ['A-ROOMS','_MKD_ROOM']
work_layers = ['Workplaces']

def select_and_visualize_layers(gdf):
    # Obtener las capas únicas del GeoDataFrame
    layers = gdf['Layer'].unique()

    # add multi layer selection
    def_select = [layer for layer in layers if layer in floor_layers]

    floor_selected_layer = st.multiselect('Select Floor layers:', layers, default=def_select ,key=f"multiselect_floor")

    def_select = [layer for layer in layers if layer in room_layers]
    room_selected_layer = st.multiselect('Select Room layers:', layers, default=def_select ,key=f"multiselect_room")

    work_selected_layer = st.multiselect('Select Workplaces layers:', layers, default=[layer for layer in layers if layer in work_layers], key=f"multiselect_work")

    selected_layer = floor_selected_layer + work_selected_layer + room_selected_layer

    # Filtrar el GeoDataFrame por la capa seleccionada
    
    filtered_gdf = gdf[gdf['Layer'].isin(selected_layer)]

    floor_selected_layer = gdf[gdf['Layer'].isin(floor_selected_layer)]
    room_selected_layer = gdf[gdf['Layer'].isin(room_selected_layer)]
    work_selected_layer = gdf[gdf['Layer'].isin(work_selected_layer)]

    return filtered_gdf , floor_selected_layer , work_selected_layer, room_selected_layer


