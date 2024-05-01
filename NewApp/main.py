from streamlit_option_menu import option_menu
from Geo_reference import mainGeo
from NewMultiplesFiles import mainFiles
import streamlit as st

def main():
    st.set_page_config(layout="centered")  # Configurar el ancho y alto del lienzo

    # Menú horizontal para seleccionar entre las dos aplicaciones
    selected = option_menu(
        menu_title=None,
        options=["ConvertGeojson", "Georeferencer"],
        icons=["arrow-clockwise", "globe-europe-africa"],
        default_index=0,
        orientation="horizontal",
    )

    # Según la opción seleccionada, ejecuta la función correspondiente
    if selected == "ConvertGeojson":
        mainFiles()
    elif selected == "Georeferencer":
        mainGeo()
        
if __name__ == "__main__":
    main()