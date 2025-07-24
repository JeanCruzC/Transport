import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from datetime import timedelta
import requests
from math import radians, sin, cos, sqrt, atan2


@st.cache_data
def geocodificar_direccion(direccion: str):
    """Devuelve posibles coincidencias para una dirección usando Nominatim."""
    if not direccion:
        return []
    try:
        respuesta = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": direccion, "format": "json", "limit": 5},
            headers={"User-Agent": "streamlit-app"},
            timeout=10,
        )
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.RequestException:
        return []


def geocodificacion_inversa(lat, lon):
    """Obtiene la dirección a partir de coordenadas."""
    try:
        respuesta = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'addressdetails': 1,
                'zoom': 18
            },
            headers={"User-Agent": "streamlit-app"},
            timeout=10,
        )
        respuesta.raise_for_status()
        data = respuesta.json()
        return data.get('display_name', f'Coordenadas: {lat:.4f}, {lon:.4f}')
    except requests.RequestException:
        return f'Coordenadas: {lat:.4f}, {lon:.4f}'


def calcular_distancia(lat1, lon1, lat2, lon2):
    """Calcula la distancia en kilómetros entre dos puntos."""
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c


def crear_mapa_seleccion(ubicaciones_existentes=None, zoom_inicial=6):
    """Crea un mapa interactivo para seleccionar ubicaciones."""
    mapa = folium.Map(
        location=[-9.19, -75.0152], 
        zoom_start=zoom_inicial,
        tiles='OpenStreetMap'
    )
    
    # Agregar marcadores existentes si los hay
    if ubicaciones_existentes:
        for nombre, datos in ubicaciones_existentes.items():
            color = 'green' if datos.get('tipo') == 'origen' else 'red'
            icon = 'play' if datos.get('tipo') == 'origen' else 'stop'
            
            folium.Marker(
                [datos['lat'], datos['lon']],
                popup=f"{datos['tipo'].title()}: {nombre}",
                icon=folium.Icon(color=color, icon=icon)
            ).add_to(mapa)
    
    return mapa


def procesar_click_mapa(data_mapa, tipo_ubicacion):
    """Procesa el click en el mapa y extrae las coordenadas."""
    if data_mapa['last_clicked'] is not None:
        lat = data_mapa['last_clicked']['lat']
        lon = data_mapa['last_clicked']['lng']
        
        # Obtener dirección aproximada
        direccion = geocodificacion_inversa(lat, lon)
        
        return {
            'lat': lat,
            'lon': lon,
            'display_name': direccion,
            'tipo': tipo_ubicacion,
            'metodo_seleccion': 'mapa'
        }
    
    return None


# Configuración de la página
st.set_page_config(
    page_title="Gestión de Rutas de Transporte",
    page_icon="🚛",
    layout="wide"
)

# Función para inicializar datos de ejemplo
@st.cache_data
def load_sample_data():
    # Datos de conductores
    conductores = pd.DataFrame({
        'id': range(1, 11),
        'nombre': ['Juan Pérez', 'María García', 'Carlos López', 'Ana Martín', 'Luis Rodríguez',
                  'Carmen Sánchez', 'Pedro González', 'Laura Fernández', 'Miguel Torres', 'Isabel Ruiz'],
        'licencia': ['A123456', 'B789012', 'C345678', 'D901234', 'E567890',
                    'F123456', 'G789012', 'H345678', 'I901234', 'J567890'],
        'telefono': ['555-0101', '555-0102', '555-0103', '555-0104', '555-0105',
                    '555-0106', '555-0107', '555-0108', '555-0109', '555-0110'],
        'vehiculo': ['Camión A', 'Furgoneta B', 'Camión C', 'Van D', 'Camión E',
                    'Furgoneta F', 'Camión G', 'Van H', 'Camión I', 'Furgoneta J'],
        'estado': ['Activo', 'Activo', 'En ruta', 'Activo', 'En ruta',
                  'Descanso', 'Activo', 'En ruta', 'Activo', 'Mantenimiento']
    })
    
    # Datos de rutas
    rutas = pd.DataFrame({
        'id': range(1, 21),
        'conductor_id': [1, 1, 2, 2, 3, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 6, 7],
        'origen': ['Lima', 'Arequipa', 'Cusco', 'Lima', 'Trujillo', 'Lima', 'Piura', 'Iquitos', 
                  'Huancayo', 'Chiclayo', 'Lima', 'Tacna', 'Ayacucho', 'Callao', 'Ica', 
                  'Cajamarca', 'Puno', 'Tumbes', 'Huánuco', 'Moquegua'],
        'destino': ['Arequipa', 'Lima', 'Lima', 'Cusco', 'Lima', 'Trujillo', 'Lima', 'Lima',
                   'Lima', 'Lima', 'Chiclayo', 'Lima', 'Lima', 'Ica', 'Lima',
                   'Lima', 'Cusco', 'Piura', 'Lima', 'Tacna'],
        'distancia_km': [1000, 1000, 1100, 1100, 560, 560, 970, 1800, 300, 770,
                        770, 1200, 550, 150, 300, 850, 390, 1300, 410, 450],
        'fecha_inicio': pd.date_range('2024-01-01', periods=20, freq='2D'),
        'fecha_fin': pd.date_range('2024-01-02', periods=20, freq='2D'),
        'estado': ['Completada', 'En progreso', 'Completada', 'Planificada', 'En progreso',
                  'Completada', 'Planificada', 'Completada', 'En progreso', 'Completada',
                  'Planificada', 'Completada', 'En progreso', 'Completada', 'Planificada',
                  'En progreso', 'Completada', 'Planificada', 'En progreso', 'Completada'],
        'carga_kg': [5000, 7500, 3200, 8000, 4500, 6000, 5500, 2800, 4000, 6500,
                    3800, 7200, 4200, 5800, 3500, 6800, 4800, 5200, 3900, 6200]
    })
    
    # Coordenadas de ciudades principales del Perú
    coordenadas = {
        'Lima': [-12.0464, -77.0428],
        'Arequipa': [-16.4090, -71.5375],
        'Cusco': [-13.5319, -71.9675],
        'Trujillo': [-8.1116, -79.0291],
        'Piura': [-5.1945, -80.6328],
        'Iquitos': [-3.7437, -73.2516],
        'Huancayo': [-12.0685, -75.2049],
        'Chiclayo': [-6.7714, -79.8391],
        'Tacna': [-18.0148, -70.2533],
        'Ayacucho': [-13.1631, -74.2236],
        'Callao': [-12.0566, -77.1181],
        'Ica': [-14.0678, -75.7286],
        'Cajamarca': [-7.1638, -78.5005],
        'Puno': [-15.8422, -70.0199],
        'Tumbes': [-3.5669, -80.4515],
        'Huánuco': [-9.9306, -76.2422],
        'Moquegua': [-17.1934, -70.9348]
    }
    
    return conductores, rutas, coordenadas

# Cargar datos y almacenar en session_state
conductores_default, rutas_default, coordenadas_dict = load_sample_data()

if 'conductores_df' not in st.session_state:
    st.session_state['conductores_df'] = conductores_default.copy()
if 'rutas_df' not in st.session_state:
    st.session_state['rutas_df'] = rutas_default.copy()
if 'direccion_origen_seleccionada' not in st.session_state:
    st.session_state['direccion_origen_seleccionada'] = None
if 'direccion_destino_seleccionada' not in st.session_state:
    st.session_state['direccion_destino_seleccionada'] = None
if 'resultados_origen' not in st.session_state:
    st.session_state['resultados_origen'] = []
if 'resultados_destino' not in st.session_state:
    st.session_state['resultados_destino'] = []
if 'distancia_calculada' not in st.session_state:
    st.session_state['distancia_calculada'] = None
if 'ubicacion_temporal' not in st.session_state:
    st.session_state['ubicacion_temporal'] = None

conductores_df = st.session_state['conductores_df']
rutas_df = st.session_state['rutas_df']

# Sidebar para navegación
st.sidebar.title("🚛 Gestión de Rutas")
pagina = st.sidebar.selectbox(
    "Seleccionar página:",
    ["Dashboard", "Conductores", "Rutas", "Mapa de Rutas", "Análisis"]
)

if pagina == "Dashboard":
    st.title("📊 Dashboard de Transporte")
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Conductores", len(conductores_df))
    
    with col2:
        rutas_activas = len(rutas_df[rutas_df['estado'] == 'En progreso'])
        st.metric("Rutas Activas", rutas_activas)
    
    with col3:
        distancia_total = rutas_df['distancia_km'].sum()
        st.metric("Distancia Total (km)", f"{distancia_total:,}")
    
    with col4:
        carga_total = rutas_df['carga_kg'].sum()
        st.metric("Carga Total (kg)", f"{carga_total:,}")
    
    # Gráficos de resumen
    col1, col2 = st.columns(2)
    
    with col1:
        # Estado de conductores
        estado_conductores = conductores_df['estado'].value_counts()
        fig_conductores = px.pie(
            values=estado_conductores.values,
            names=estado_conductores.index,
            title="Estado de Conductores"
        )
        st.plotly_chart(fig_conductores, use_container_width=True)
    
    with col2:
        # Estado de rutas
        estado_rutas = rutas_df['estado'].value_counts()
        fig_rutas = px.pie(
            values=estado_rutas.values,
            names=estado_rutas.index,
            title="Estado de Rutas"
        )
        st.plotly_chart(fig_rutas, use_container_width=True)
    
    # Rutas por conductor
    rutas_por_conductor = rutas_df.groupby('conductor_id').size().reset_index(name='num_rutas')
    rutas_por_conductor = rutas_por_conductor.merge(
        conductores_df[['id', 'nombre']], 
        left_on='conductor_id', 
        right_on='id'
    )
    
    fig_bar = px.bar(
        rutas_por_conductor,
        x='nombre',
        y='num_rutas',
        title="Número de Rutas por Conductor",
        labels={'num_rutas': 'Número de Rutas', 'nombre': 'Conductor'}
    )
    fig_bar.update_xaxes(tickangle=45)
    st.plotly_chart(fig_bar, use_container_width=True)

elif pagina == "Conductores":
    st.title("👨‍💼 Gestión de Conductores")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        filtro_estado = st.selectbox("Filtrar por estado:", ["Todos"] + list(conductores_df['estado'].unique()))
    
    # Aplicar filtros
    conductores_filtrados = conductores_df.copy()
    if filtro_estado != "Todos":
        conductores_filtrados = conductores_filtrados[conductores_filtrados['estado'] == filtro_estado]
    
    # Mostrar tabla de conductores
    st.subheader("Lista de Conductores")
    st.dataframe(conductores_filtrados, use_container_width=True)
    
    # Formulario para agregar conductor
    with st.expander("➕ Agregar Nuevo Conductor"):
        with st.form("nuevo_conductor"):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre completo")
                licencia = st.text_input("Número de licencia")
                telefono = st.text_input("Teléfono")
            with col2:
                vehiculo = st.text_input("Vehículo asignado")
                estado = st.selectbox("Estado", ["Activo", "En ruta", "Descanso", "Mantenimiento"])
            
            submitted = st.form_submit_button("Agregar Conductor")
            if submitted and nombre and licencia:
                nuevo_id = int(st.session_state['conductores_df']['id'].max()) + 1 if not st.session_state['conductores_df'].empty else 1
                nuevo_conductor = {
                    'id': nuevo_id,
                    'nombre': nombre,
                    'licencia': licencia,
                    'telefono': telefono,
                    'vehiculo': vehiculo,
                    'estado': estado
                }
                st.session_state['conductores_df'] = pd.concat([
                    st.session_state['conductores_df'],
                    pd.DataFrame([nuevo_conductor])
                ], ignore_index=True)
                st.success(f"Conductor {nombre} agregado exitosamente!")

elif pagina == "Rutas":
    st.title("🗺️ Gestión de Rutas")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_conductor = st.selectbox(
            "Filtrar por conductor:", 
            ["Todos"] + list(conductores_df['nombre'].values)
        )
    with col2:
        filtro_estado_ruta = st.selectbox(
            "Filtrar por estado:", 
            ["Todos"] + list(rutas_df['estado'].unique())
        )
    with col3:
        filtro_fecha = st.date_input("Filtrar desde fecha:")

    # Aplicar filtros
    rutas_filtradas = rutas_df.copy()
    
    if filtro_conductor != "Todos":
        conductor_id = conductores_df[conductores_df['nombre'] == filtro_conductor]['id'].iloc[0]
        rutas_filtradas = rutas_filtradas[rutas_filtradas['conductor_id'] == conductor_id]
    
    if filtro_estado_ruta != "Todos":
        rutas_filtradas = rutas_filtradas[rutas_filtradas['estado'] == filtro_estado_ruta]

    # Filtrar por fecha de inicio si se ha seleccionado una
    if filtro_fecha:
        rutas_filtradas = rutas_filtradas[rutas_filtradas['fecha_inicio'] >= pd.to_datetime(filtro_fecha)]
    
    # Agregar nombre del conductor a las rutas
    rutas_con_conductor = rutas_filtradas.merge(
        conductores_df[['id', 'nombre']], 
        left_on='conductor_id', 
        right_on='id',
        suffixes=('', '_conductor')
    )
    
    # Mostrar tabla de rutas
    st.subheader("Lista de Rutas")
    columnas_mostrar = ['id', 'nombre', 'origen', 'destino', 'distancia_km', 
                       'fecha_inicio', 'fecha_fin', 'estado', 'carga_kg']
    st.dataframe(rutas_con_conductor[columnas_mostrar], use_container_width=True)
    
    # Formulario para agregar ruta con tabs
    with st.expander("➕ Planificar Nueva Ruta"):
        st.markdown("### 🎯 Selección de Ubicaciones")
        
        # Tabs para diferentes modos de selección
        tab1, tab2 = st.tabs(["🔍 Búsqueda por Texto", "🗺️ Selección en Mapa"])
        
        # TAB 1: Búsqueda por texto (código original mejorado)
        with tab1:
            st.markdown("**Busca direcciones escribiendo la dirección:**")
            
            col_busqueda1, col_busqueda2 = st.columns(2)
            with col_busqueda1:
                st.subheader("📍 Origen")
                direccion_origen = st.text_input("Dirección de origen", key="direccion_origen_input")
                if st.button("🔍 Buscar Origen", key="buscar_origen_texto"):
                    with st.spinner("Buscando origen..."):
                        st.session_state['resultados_origen'] = geocodificar_direccion(direccion_origen)
                
                for i, res in enumerate(st.session_state.get('resultados_origen', [])):
                    st.write(f"📍 {res.get('display_name')}")
                    if st.button("Seleccionar", key=f"sel_origen_texto_{i}"):
                        res['metodo_seleccion'] = 'busqueda'
                        st.session_state['direccion_origen_seleccionada'] = res
                        st.session_state['resultados_origen'] = []
                        st.success("✅ Origen seleccionado!")
                        st.rerun()

            with col_busqueda2:
                st.subheader("🎯 Destino")
                direccion_destino = st.text_input("Dirección de destino", key="direccion_destino_input")
                if st.button("🔍 Buscar Destino", key="buscar_destino_texto"):
                    with st.spinner("Buscando destino..."):
                        st.session_state['resultados_destino'] = geocodificar_direccion(direccion_destino)
                
                for i, res in enumerate(st.session_state.get('resultados_destino', [])):
                    st.write(f"🎯 {res.get('display_name')}")
                    if st.button("Seleccionar", key=f"sel_destino_texto_{i}"):
                        res['metodo_seleccion'] = 'busqueda'
                        st.session_state['direccion_destino_seleccionada'] = res
                        st.session_state['resultados_destino'] = []
                        st.success("✅ Destino seleccionado!")
                        st.rerun()
        
        # TAB 2: Selección en mapa (nueva funcionalidad)
        with tab2:
            st.markdown("**Haz clic en el mapa para seleccionar ubicaciones:**")
            
            # Instrucciones visuales
            st.markdown("""
            <div style='background-color: #f0f8ff; padding: 10px; border-radius: 5px; margin: 10px 0;'>
            <h4>🗺️ Instrucciones:</h4>
            <ul>
            <li><strong>1.</strong> Elige si vas a marcar origen o destino</li>
            <li><strong>2.</strong> Haz clic en cualquier punto del mapa</li>
            <li><strong>3.</strong> Confirma la ubicación seleccionada</li>
            <li><strong>4.</strong> Repite para la segunda ubicación</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
            # Selector de qué ubicación se está marcando
            col1, col2 = st.columns(2)
            with col1:
                seleccionando = st.radio(
                    "¿Qué ubicación estás seleccionando?",
                    ["📍 Origen", "🎯 Destino"],
                    key="radio_seleccion_mapa"
                )
            
            with col2:
                if st.button("🔄 Limpiar Selecciones", key="limpiar_mapa"):
                    st.session_state['direccion_origen_seleccionada'] = None
                    st.session_state['direccion_destino_seleccionada'] = None
                    st.session_state['ubicacion_temporal'] = None
                    st.rerun()
            
            # Preparar ubicaciones existentes para mostrar en el mapa
            ubicaciones_para_mapa = {}
            if st.session_state['direccion_origen_seleccionada']:
                origen = st.session_state['direccion_origen_seleccionada']
                ubicaciones_para_mapa['Origen'] = {
                    'lat': float(origen['lat']),
                    'lon': float(origen['lon']),
                    'tipo': 'origen'
                }

            if st.session_state['direccion_destino_seleccionada']:
                destino = st.session_state['direccion_destino_seleccionada']
                ubicaciones_para_mapa['Destino'] = {
                    'lat': float(destino['lat']),
                    'lon': float(destino['lon']),
                    'tipo': 'destino'
                }

            # Crear y mostrar el mapa interactivo
            mapa_seleccion = crear_mapa_seleccion(ubicaciones_para_mapa)

            # Mostrar el mapa y capturar interacciones
            map_data = st_folium(
                mapa_seleccion, 
                width=700, 
                height=400,
                key="mapa_seleccion_ubicaciones"
            )

            # Procesar clicks en el mapa
            if map_data['last_clicked'] is not None:
                tipo_seleccionando = "origen" if "Origen" in seleccionando else "destino"
                
                ubicacion_seleccionada = procesar_click_mapa(map_data, tipo_seleccionando)
                
                if ubicacion_seleccionada:
                    st.session_state['ubicacion_temporal'] = ubicacion_seleccionada
                    
                    st.info(f"📍 **Ubicación seleccionada para {tipo_seleccionando}:**")
                    st.write(f"**Coordenadas:** {ubicacion_seleccionada['lat']:.4f}, {ubicacion_seleccionada['lon']:.4f}")
                    st.write(f"**Dirección aproximada:** {ubicacion_seleccionada['display_name']}")
                    
                    # Botón para confirmar la selección
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button(f"✅ Confirmar {tipo_seleccionando.title()}", key=f"confirmar_{tipo_seleccionando}_mapa"):
                            if tipo_seleccionando == "origen":
                                st.session_state['direccion_origen_seleccionada'] = ubicacion_seleccionada
                            else:
                                st.session_state['direccion_destino_seleccionada'] = ubicacion_seleccionada
                            
                            st.session_state['ubicacion_temporal'] = None
                            st.success(f"✅ {tipo_seleccionando.title()} confirmado!")
                            st.rerun()
                    
                    with col2:
                        st.write("👆 Confirma la selección o haz clic en otro punto del mapa")
        
        # Mostrar resumen de ubicaciones seleccionadas (en ambos tabs)
        st.markdown("---")
        st.markdown("### 📋 Ubicaciones Seleccionadas")

        col1, col2 = st.columns(2)

        with col1:
            if st.session_state['direccion_origen_seleccionada']:
                origen = st.session_state['direccion_origen_seleccionada']
                metodo = origen.get('metodo_seleccion', 'busqueda')
                icono_metodo = "🗺️" if metodo == 'mapa' else "🔍"
                
                st.success(f"✅ **Origen** {icono_metodo}")
                st.write(f"📍 {origen.get('display_name', 'N/A')}")
                st.write(f"📐 Coords: {float(origen['lat']):.4f}, {float(origen['lon']):.4f}")
                
                if st.button("❌ Quitar Origen", key="quitar_origen"):
                    st.session_state['direccion_origen_seleccionada'] = None
                    st.rerun()
            else:
                st.info("📍 **Origen no seleccionado**")
                st.write("Usa la búsqueda por texto o selecciona en el mapa")

        with col2:
            if st.session_state['direccion_destino_seleccionada']:
                destino = st.session_state['direccion_destino_seleccionada']
                metodo = destino.get('metodo_seleccion', 'busqueda')
                icono_metodo = "🗺️" if metodo == 'mapa' else "🔍"
                
                st.success(f"✅ **Destino** {icono_metodo}")
                st.write(f"🎯 {destino.get('display_name', 'N/A')}")
                st.write(f"📐 Coords: {float(destino['lat']):.4f}, {float(destino['lon']):.4f}")
                
                if st.button("❌ Quitar Destino", key="quitar_destino"):
                    st.session_state['direccion_destino_seleccionada'] = None
                    st.rerun()
            else:
                st.info("🎯 **Destino no seleccionado**")
                st.write("Usa la búsqueda por texto o selecciona en el mapa")

        # Formulario principal para crear la ruta
        origen_sel = st.session_state.get('direccion_origen_seleccionada')
        destino_sel = st.session_state.get('direccion_destino_seleccionada')

        if origen_sel and destino_sel:
            lat1, lon1 = float(origen_sel['lat']), float(origen_sel['lon'])
            lat2, lon2 = float(destino_sel['lat']), float(destino_sel['lon'])
            distancia = calcular_distancia(lat1, lon1, lat2, lon2)
            st.session_state['distancia_calculada'] = distancia
            
            # Mostrar información de métodos de selección
            metodo_origen = "🗺️ Mapa" if origen_sel.get('metodo_seleccion') == 'mapa' else "🔍 Búsqueda"
            metodo_destino = "🗺️ Mapa" if destino_sel.get('metodo_seleccion') == 'mapa' else "🔍 Búsqueda"
            
            st.success(f"📊 **Ruta calculada:** {distancia:.1f} km")
            st.write(f"**Origen seleccionado via:** {metodo_origen}")
            st.write(f"**Destino seleccionado via:** {metodo_destino}")

            # Vista previa del mapa mejorada
            st.markdown("### 🗺️ Vista Previa de la Ruta")
            mapa_prev = folium.Map(location=[(lat1 + lat2) / 2, (lon1 + lon2) / 2], zoom_start=8)
            
            folium.Marker(
                [lat1, lon1], 
                popup=f"<b>Origen</b><br>{origen_sel.get('display_name', 'N/A')}<br>Método: {metodo_origen}",
                icon=folium.Icon(color='green', icon='play')
            ).add_to(mapa_prev)
            
            folium.Marker(
                [lat2, lon2], 
                popup=f"<b>Destino</b><br>{destino_sel.get('display_name', 'N/A')}<br>Método: {metodo_destino}",
                icon=folium.Icon(color='red', icon='stop')
            ).add_to(mapa_prev)
            
            folium.PolyLine(
                [[lat1, lon1], [lat2, lon2]], 
                color="blue", 
                weight=4, 
                opacity=0.8,
                popup=f"Distancia: {distancia:.1f} km"
            ).add_to(mapa_prev)
            
            st_folium(mapa_prev, width=700, height=300)

            # Formulario final para crear la ruta
            st.markdown("### 📋 Detalles de la Ruta")
            with st.form("nueva_ruta"):
                col1, col2 = st.columns(2)
                
                with col1:
                    conductor_seleccionado = st.selectbox("👨‍💼 Conductor", conductores_df['nombre'].values)
                    carga_ruta = st.number_input("📦 Carga (kg)", min_value=1, value=1000)
                    
                with col2:
                    distancia_ruta = st.number_input(
                        "📏 Distancia (km)", 
                        value=float(distancia), 
                        format="%.2f",
                        help=f"Distancia calculada automáticamente: {distancia:.1f} km"
                    )
                    fecha_inicio_ruta = st.date_input("📅 Fecha de inicio")

                submitted_ruta = st.form_submit_button("🚛 Crear Ruta", use_container_width=True)
                
                if submitted_ruta:
                    conductor_id = st.session_state['conductores_df'][
                        st.session_state['conductores_df']['nombre'] == conductor_seleccionado
                    ]['id'].iloc[0]
                    
                    nuevo_id = int(st.session_state['rutas_df']['id'].max()) + 1 if not st.session_state['rutas_df'].empty else 1
                    
                    # Crear nombres descriptivos para origen y destino
                    origen_nombre = origen_sel.get('display_name', '').split(',')[0][:50]
                    destino_nombre = destino_sel.get('display_name', '').split(',')[0][:50]
                    
                    # Agregar al diccionario de coordenadas
                    coordenadas_dict[origen_nombre] = [lat1, lon1]
                    coordenadas_dict[destino_nombre] = [lat2, lon2]
                    
                    nueva_ruta = {
                        'id': nuevo_id,
                        'conductor_id': conductor_id,
                        'origen': origen_nombre,
                        'destino': destino_nombre,
                        'distancia_km': distancia,
                        'fecha_inicio': pd.to_datetime(fecha_inicio_ruta),
                        'fecha_fin': pd.to_datetime(fecha_inicio_ruta) + timedelta(days=1),
                        'estado': 'Planificada',
                        'carga_kg': carga_ruta
                    }
                    
                    st.session_state['rutas_df'] = pd.concat([
                        st.session_state['rutas_df'],
                        pd.DataFrame([nueva_ruta])
                    ], ignore_index=True)
                    
                    st.success(f"🎉 Ruta creada: {origen_nombre} → {destino_nombre}")
                    st.success(f"📊 Distancia: {distancia:.1f} km | Carga: {carga_ruta} kg | Conductor: {conductor_seleccionado}")
                    
                    # Limpiar variables de sesión
                    st.session_state['direccion_origen_seleccionada'] = None
                    st.session_state['direccion_destino_seleccionada'] = None
                    st.session_state['distancia_calculada'] = None
                    st.session_state['ubicacion_temporal'] = None
                    st.session_state['resultados_origen'] = []
                    st.session_state['resultados_destino'] = []
                    
                    st.rerun()
        else:
            st.info("💡 Selecciona tanto el origen como el destino para continuar con la planificación de la ruta.")

elif pagina == "Mapa de Rutas":
    st.title("🗺️ Visualización de Rutas")
    
    # Selector de conductor
    conductor_seleccionado = st.selectbox(
        "Seleccionar conductor para ver sus rutas:",
        ["Todos"] + list(conductores_df['nombre'].values)
    )
    
    # Crear mapa centrado en Perú
    mapa = folium.Map(location=[-9.19, -75.0152], zoom_start=6)
    
    # Filtrar rutas según el conductor seleccionado
    if conductor_seleccionado != "Todos":
        conductor_id = conductores_df[conductores_df['nombre'] == conductor_seleccionado]['id'].iloc[0]
        rutas_mapa = rutas_df[rutas_df['conductor_id'] == conductor_id]
    else:
        rutas_mapa = rutas_df
    
    # Colores para diferentes estados
    colores_estado = {
        'Completada': 'green',
        'En progreso': 'red',
        'Planificada': 'blue'
    }
    
    # Agregar marcadores y líneas para cada ruta
    for _, ruta in rutas_mapa.iterrows():
        if ruta['origen'] in coordenadas_dict and ruta['destino'] in coordenadas_dict:
            # Coordenadas de origen y destino
            coord_origen = coordenadas_dict[ruta['origen']]
            coord_destino = coordenadas_dict[ruta['destino']]
            
            # Color según el estado
            color = colores_estado.get(ruta['estado'], 'gray')
            
            # Marcador de origen
            folium.Marker(
                coord_origen,
                popup=f"Origen: {ruta['origen']}<br>Ruta ID: {ruta['id']}",
                icon=folium.Icon(color=color, icon='play')
            ).add_to(mapa)
            
            # Marcador de destino
            folium.Marker(
                coord_destino,
                popup=f"Destino: {ruta['destino']}<br>Ruta ID: {ruta['id']}",
                icon=folium.Icon(color=color, icon='stop')
            ).add_to(mapa)
            
            # Línea de la ruta
            folium.PolyLine(
                [coord_origen, coord_destino],
                color=color,
                weight=3,
                opacity=0.7,
                popup=f"Ruta {ruta['id']}: {ruta['origen']} → {ruta['destino']}<br>Estado: {ruta['estado']}<br>Distancia: {ruta['distancia_km']} km"
            ).add_to(mapa)
    
    # Agregar leyenda
    leyenda_html = '''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 150px; height: 90px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <b>Estado de Rutas</b><br>
    <i class="fa fa-circle" style="color:green"></i> Completada<br>
    <i class="fa fa-circle" style="color:red"></i> En progreso<br>
    <i class="fa fa-circle" style="color:blue"></i> Planificada<br>
    </div>
    '''
    mapa.get_root().html.add_child(folium.Element(leyenda_html))
    
    # Mostrar el mapa
    st_folium(mapa, width=700, height=500)

elif pagina == "Análisis":
    st.title("📈 Análisis de Rendimiento")
    
    # Análisis de distancias
    col1, col2 = st.columns(2)
    
    with col1:
        # Distancia por conductor
        distancia_conductor = rutas_df.groupby('conductor_id')['distancia_km'].sum().reset_index()
        distancia_conductor = distancia_conductor.merge(
            conductores_df[['id', 'nombre']], 
            left_on='conductor_id', 
            right_on='id'
        )
        
        fig_distancia = px.bar(
            distancia_conductor,
            x='nombre',
            y='distancia_km',
            title="Distancia Total por Conductor (km)",
            labels={'distancia_km': 'Distancia (km)', 'nombre': 'Conductor'}
        )
        fig_distancia.update_xaxes(tickangle=45)
        st.plotly_chart(fig_distancia, use_container_width=True)
    
    with col2:
        # Carga por conductor
        carga_conductor = rutas_df.groupby('conductor_id')['carga_kg'].sum().reset_index()
        carga_conductor = carga_conductor.merge(
            conductores_df[['id', 'nombre']], 
            left_on='conductor_id', 
            right_on='id'
        )
        
        fig_carga = px.bar(
            carga_conductor,
            x='nombre',
            y='carga_kg',
            title="Carga Total por Conductor (kg)",
            labels={'carga_kg': 'Carga (kg)', 'nombre': 'Conductor'}
        )
        fig_carga.update_xaxes(tickangle=45)
        st.plotly_chart(fig_carga, use_container_width=True)
    
    # Análisis temporal
    rutas_temp = rutas_df.copy()
    rutas_temp['fecha_inicio'] = pd.to_datetime(rutas_temp['fecha_inicio'])
    rutas_temporales = rutas_temp.groupby(rutas_temp['fecha_inicio'].dt.date).size().reset_index(name='num_rutas')
    
    fig_temporal = px.line(
        rutas_temporales,
        x='fecha_inicio',
        y='num_rutas',
        title="Rutas Programadas por Día",
        labels={'num_rutas': 'Número de Rutas', 'fecha_inicio': 'Fecha'}
    )
    st.plotly_chart(fig_temporal, use_container_width=True)
    
    # Tabla de resumen por conductor
    st.subheader("Resumen por Conductor")
    resumen = rutas_df.groupby('conductor_id').agg({
        'distancia_km': ['sum', 'mean', 'count'],
        'carga_kg': ['sum', 'mean']
    }).round(2)
    
    resumen.columns = ['Distancia Total', 'Distancia Promedio', 'Num. Rutas', 'Carga Total', 'Carga Promedio']
    resumen = resumen.merge(
        conductores_df[['id', 'nombre']], 
        left_index=True, 
        right_on='id'
    ).set_index('nombre')
    
    st.dataframe(resumen, use_container_width=True)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("🚛 **Gestión de Rutas de Transporte**")
st.sidebar.markdown("Desarrollado con Streamlit")
