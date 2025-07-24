import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

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

# Cargar datos
conductores_df, rutas_df, coordenadas_dict = load_sample_data()

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
    fig_bar.update_xaxis(tickangle=45)
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
    
    # Formulario para agregar ruta
    with st.expander("➕ Planificar Nueva Ruta"):
        with st.form("nueva_ruta"):
            col1, col2 = st.columns(2)
            with col1:
                conductor_seleccionado = st.selectbox("Conductor", conductores_df['nombre'].values)
                origen_ruta = st.selectbox("Origen", list(coordenadas_dict.keys()))
                destino_ruta = st.selectbox("Destino", list(coordenadas_dict.keys()))
            with col2:
                distancia_ruta = st.number_input("Distancia (km)", min_value=1, value=100)
                carga_ruta = st.number_input("Carga (kg)", min_value=1, value=1000)
                fecha_inicio_ruta = st.date_input("Fecha de inicio")
            
            submitted_ruta = st.form_submit_button("Planificar Ruta")
            if submitted_ruta:
                st.success(f"Ruta {origen_ruta} → {destino_ruta} planificada para {conductor_seleccionado}!")

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
        fig_distancia.update_xaxis(tickangle=45)
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
        fig_carga.update_xaxis(tickangle=45)
        st.plotly_chart(fig_carga, use_container_width=True)
    
    # Análisis temporal
    rutas_df['fecha_inicio'] = pd.to_datetime(rutas_df['fecha_inicio'])
    rutas_temporales = rutas_df.groupby(rutas_df['fecha_inicio'].dt.date).size().reset_index(name='num_rutas')
    
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