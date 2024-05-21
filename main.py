from streamlit_option_menu import option_menu
#from NewApp.Geo_reference import mainGeo
from NewApp.NewGeoreferencer import mainGeo
from NewApp.NewMultiplesFiles import mainFiles
import streamlit as st

def main():
    st.set_page_config(layout="centered")  # Configurar el ancho y alto del lienzo

    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

    hide_table_row_index = """
        <style>
        thead tr th:first-child {display:none}
        tbody th {display:none}
        </style>
        """
    st.markdown(hide_table_row_index, unsafe_allow_html=True)

    st.write("# Welcome! 👋🏾​​")

    st.write("**This tool is designed to help you convert your floor plans into a format that can be used in your leaflet map.**")

    st.write("**To get started, select a tool from the bar.**")

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