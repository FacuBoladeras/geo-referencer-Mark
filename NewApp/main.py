from streamlit_option_menu import option_menu
from NewFuncs.Geo_reference import mainGeo
from NewFuncs.NewMultiplesFiles import mainFiles
import streamlit as st

def main():
    st.set_page_config(layout="wide")  # Configurar el ancho y alto del lienzo

    # Menú horizontal para seleccionar entre las dos aplicaciones
    selected = option_menu(
        menu_title=None,
        options=["Clientes", "Siniestros"],
        icons=["card-list", "car-front-fill"],
        default_index=0,
        orientation="horizontal",
    )

    # Según la opción seleccionada, ejecuta la función correspondiente
    if selected == "Clientes":
        mainGeo()
    elif selected == "Siniestros":
        mainFiles()
        