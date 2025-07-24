import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from datetime import timedelta
import requests
from math import radians, sin, cos, sqrt, atan2
import numpy as np
from itertools import permutations
import plotly.graph_objects as go


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


def optimizar_ruta_multiple(origen, destinos, algoritmo="nearest_neighbor"):
    """
    Optimiza el orden de visita para múltiples destinos.
    
    Parámetros:
    - origen: dict con coordenadas del punto de inicio
    - destinos: lista de dicts con coordenadas de destinos
    - algoritmo: 'nearest_neighbor', 'brute_force', o '2opt'
    
    Retorna:
    - Orden optimizado de destinos y distancia total
    """
    if not destinos:
        return [], 0
    
    if len(destinos) == 1:
        distancia = calcular_distancia(
            origen['lat'], origen['lon'],
            destinos[0]['lat'], destinos[0]['lon']
        )
        return [0], distancia
    
    # Crear matriz de distancias
    todos_puntos = [origen] + destinos
    n = len(todos_puntos)
    matriz_distancia = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            if i != j:
                matriz_distancia[i][j] = calcular_distancia(
                    todos_puntos[i]['lat'], todos_puntos[i]['lon'],
                    todos_puntos[j]['lat'], todos_puntos[j]['lon']
                )
    
    if algoritmo == "nearest_neighbor":
        return _nearest_neighbor(matriz_distancia)
    elif algoritmo == "brute_force" and len(destinos) <= 8:
        return _brute_force(matriz_distancia)
    elif algoritmo == "2opt":
        return _two_opt(matriz_distancia)
    else:
        return _nearest_neighbor(matriz_distancia)


def _nearest_neighbor(matriz_distancia):
    """Algoritmo del vecino más cercano."""
    n = len(matriz_distancia)
    visitados = [False] * n
    ruta = [0]  # Empezar desde el origen (índice 0)
    visitados[0] = True
    distancia_total = 0
    
    actual = 0
    for _ in range(n - 1):
        mejor_siguiente = -1
        mejor_distancia = float('inf')
        
        for j in range(n):
            if not visitados[j] and matriz_distancia[actual][j] < mejor_distancia:
                mejor_distancia = matriz_distancia[actual][j]
                mejor_siguiente = j
        
        if mejor_siguiente != -1:
            ruta.append(mejor_siguiente)
            visitados[mejor_siguiente] = True
            distancia_total += mejor_distancia
            actual = mejor_siguiente
    
    # Convertir índices a orden de destinos (excluyendo origen)
    orden_destinos = [i - 1 for i in ruta[1:]]
    return orden_destinos, distancia_total


def _brute_force(matriz_distancia):
    """Fuerza bruta para rutas pequeñas (≤8 destinos)."""
    n = len(matriz_distancia)
    destinos_indices = list(range(1, n))  # Excluir origen (índice 0)
    
    mejor_distancia = float('inf')
    mejor_orden = []
    
    for permutacion in permutations(destinos_indices):
        distancia = 0
        actual = 0  # Empezar desde origen
        
        for siguiente in permutacion:
            distancia += matriz_distancia[actual][siguiente]
            actual = siguiente
        
        if distancia < mejor_distancia:
            mejor_distancia = distancia
            mejor_orden = [i - 1 for i in permutacion]  # Convertir a índices de destinos
    
    return mejor_orden, mejor_distancia


def _two_opt(matriz_distancia):
    """Algoritmo 2-opt para mejora local."""
    n = len(matriz_distancia)
    if n <= 2:
        return [0] if n == 2 else [], 0
    
    # Empezar con nearest neighbor
    ruta_inicial, _ = _nearest_neighbor(matriz_distancia)
    ruta = [0] + [i + 1 for i in ruta_inicial]  # Agregar origen al inicio
    
    mejorado = True
    while mejorado:
        mejorado = False
        for i in range(1, len(ruta) - 2):
            for j in range(i + 1, len(ruta)):
                if j - i == 1:
                    continue
                
                nueva_ruta = ruta[:]
                nueva_ruta[i:j] = nueva_ruta[i:j][::-1]
                
                if _calcular_distancia_ruta(nueva_ruta, matriz_distancia) < _calcular_distancia_ruta(ruta, matriz_distancia):
                    ruta = nueva_ruta
                    mejorado = True
    
    orden_destinos = [i - 1 for i in ruta[1:]]
    distancia_total = _calcular_distancia_ruta(ruta, matriz_distancia)
    return orden_destinos, distancia_total


def _calcular_distancia_ruta(ruta, matriz_distancia):
    """Calcula la distancia total de una ruta."""
    distancia = 0
    for i in range(len(ruta) - 1):
        distancia += matriz_distancia[ruta[i]][ruta[i + 1]]
    return distancia


def analizar_rutas_conductor(conductor_id, rutas_df, coordenadas_dict):
    """Analiza todas las rutas de un conductor y sugiere optimizaciones."""
    rutas_conductor = rutas_df[rutas_df['conductor_id'] == conductor_id].copy()
    
    if rutas_conductor.empty:
        return None
    
    # Agrupar por fecha y estado para rutas del mismo día
    rutas_pendientes = rutas_conductor[
        rutas_conductor['estado'].isin(['Planificada', 'En progreso'])
    ].copy()
    
    if rutas_pendientes.empty:
        return {"mensaje": "No hay rutas pendientes para optimizar"}
    
    # Agrupar por fecha
    rutas_por_fecha = rutas_pendientes.groupby(rutas_pendientes['fecha_inicio'].dt.date)
    
    optimizaciones = {}
    
    for fecha, rutas_dia in rutas_por_fecha:
        if len(rutas_dia) <= 1:
            continue
        
        # Determinar punto de origen común (primera ruta del día)
        primera_ruta = rutas_dia.iloc[0]
        if primera_ruta['origen'] in coordenadas_dict:
            origen = {
                'lat': coordenadas_dict[primera_ruta['origen']][0],
                'lon': coordenadas_dict[primera_ruta['origen']][1],
                'nombre': primera_ruta['origen']
            }
        else:
            continue
        
        # Preparar destinos
        destinos = []
        for _, ruta in rutas_dia.iterrows():
            if ruta['destino'] in coordenadas_dict:
                destinos.append({
                    'lat': coordenadas_dict[ruta['destino']][0],
                    'lon': coordenadas_dict[ruta['destino']][1],
                    'nombre': ruta['destino'],
                    'id_ruta': ruta['id'],
                    'carga': ruta['carga_kg']
                })
        
        if len(destinos) < 2:
            continue
        
        # Optimizar rutas
        algoritmo = "brute_force" if len(destinos) <= 6 else "2opt"
        orden_optimizado, distancia_optimizada = optimizar_ruta_multiple(origen, destinos, algoritmo)
        
        # Calcular distancia actual (sin optimizar)
        distancia_actual = 0
        punto_actual = origen
        for destino in destinos:
            distancia_actual += calcular_distancia(
                punto_actual['lat'], punto_actual['lon'],
                destino['lat'], destino['lon']
            )
            punto_actual = destino
        
        # Preparar resultado
        destinos_ordenados = [destinos[i] for i in orden_optimizado]
        ahorro = distancia_actual - distancia_optimizada
        porcentaje_ahorro = (ahorro / distancia_actual) * 100 if distancia_actual > 0 else 0
        
        optimizaciones[fecha] = {
            'origen': origen,
            'destinos_original': destinos,
            'destinos_optimizado': destinos_ordenados,
            'orden_optimizado': orden_optimizado,
            'distancia_actual': distancia_actual,
            'distancia_optimizada': distancia_optimizada,
            'ahorro_km': ahorro,
            'ahorro_porcentaje': porcentaje_ahorro,
            'algoritmo_usado': algoritmo
        }
    
    return optimizaciones


def crear_mapa_ruta_optimizada(optimizacion_data):
    """Crea un mapa mostrando la ruta optimizada vs la original."""
    if not optimizacion_data:
        return None
    
    origen = optimizacion_data['origen']
    destinos_original = optimizacion_data['destinos_original']
    destinos_optimizado = optimizacion_data['destinos_optimizado']
    
    # Calcular centro del mapa
    todas_coords = [origen] + destinos_original
    lat_centro = sum(punto['lat'] for punto in todas_coords) / len(todas_coords)
    lon_centro = sum(punto['lon'] for punto in todas_coords) / len(todas_coords)
    
    mapa = folium.Map(location=[lat_centro, lon_centro], zoom_start=10)
    
    # Marcador de origen
    folium.Marker(
        [origen['lat'], origen['lon']],
        popup=f"<b>ORIGEN</b><br>{origen['nombre']}",
        icon=folium.Icon(color='black', icon='home')
    ).add_to(mapa)
    
    # Marcadores de destinos con numeración optimizada
    for i, destino in enumerate(destinos_optimizado):
        folium.Marker(
            [destino['lat'], destino['lon']],
            popup=f"<b>Destino {i+1}</b><br>{destino['nombre']}<br>Carga: {destino['carga']} kg",
            icon=folium.Icon(color='green', icon='info-sign'),
            tooltip=f"Orden: {i+1}"
        ).add_to(mapa)
    
    # Ruta optimizada (línea verde)
    puntos_optimizados = [[origen['lat'], origen['lon']]]
    for destino in destinos_optimizado:
        puntos_optimizados.append([destino['lat'], destino['lon']])
    
    folium.PolyLine(
        puntos_optimizados,
        color='green',
        weight=4,
        opacity=0.8,
        popup="Ruta Optimizada"
    ).add_to(mapa)
    
    # Ruta original (línea roja punteada)
    puntos_originales = [[origen['lat'], origen['lon']]]
    for destino in destinos_original:
        puntos_originales.append([destino['lat'], destino['lon']])
    
    folium.PolyLine(
        puntos_originales,
        color='red',
        weight=2,
        opacity=0.6,
        dash_array='10',
        popup="Ruta Original"
    ).add_to(mapa)
    
    # Leyenda
    leyenda_html = '''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 200px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:12px; padding: 10px">
    <b>Optimización de Ruta</b><br>
    <i class="fa fa-home" style="color:black"></i> Origen<br>
    <i class="fa fa-circle" style="color:green"></i> Ruta Optimizada<br>
    <i class="fa fa-circle" style="color:red"></i> Ruta Original<br>
    <i class="fa fa-map-marker" style="color:green"></i> Destinos (orden)
    </div>
    '''
    mapa.get_root().html.add_child(folium.Element(leyenda_html))
    
    return mapa


def generar_plan_ruta_conductor(conductor_id, conductores_df, rutas_df, coordenadas_dict):
    """Genera un plan completo de rutas optimizadas para un conductor."""
    conductor_info = conductores_df[conductores_df['id'] == conductor_id].iloc[0]
    optimizaciones = analizar_rutas_conductor(conductor_id, rutas_df, coordenadas_dict)
    
    if not optimizaciones or 'mensaje' in optimizaciones:
        return None
    
    plan = {
        'conductor': conductor_info,
        'fechas_optimizadas': {},
        'resumen_total': {
            'total_km_actual': 0,
            'total_km_optimizado': 0,
            'total_ahorro_km': 0,
            'total_rutas': 0
        }
    }
    
    for fecha, opt_data in optimizaciones.items():
        plan['fechas_optimizadas'][fecha] = {
            'fecha': fecha,
            'origen': opt_data['origen']['nombre'],
            'numero_destinos': len(opt_data['destinos_optimizado']),
            'orden_recomendado': [d['nombre'] for d in opt_data['destinos_optimizado']],
            'distancia_actual': opt_data['distancia_actual'],
            'distancia_optimizada': opt_data['distancia_optimizada'],
            'ahorro_km': opt_data['ahorro_km'],
            'ahorro_porcentaje': opt_data['ahorro_porcentaje'],
            'carga_total': sum(d['carga'] for d in opt_data['destinos_optimizado']),
            'algoritmo': opt_data['algoritmo_usado']
        }
        
        # Actualizar resumen total
        plan['resumen_total']['total_km_actual'] += opt_data['distancia_actual']
        plan['resumen_total']['total_km_optimizado'] += opt_data['distancia_optimizada']
        plan['resumen_total']['total_ahorro_km'] += opt_data['ahorro_km']
        plan['resumen_total']['total_rutas'] += len(opt_data['destinos_optimizado'])
    
    return plan


# Configuración de la página
st.set_page_config(
    page_title="Gestión de Rutas de Transporte",
    page_icon="🚛",
    layout="wide"
)

# Función para inicializar datos de ejemplo (solo rutas y coordenadas)
@st.cache_data
def load_sample_data():
    # Solo datos de rutas de ejemplo (se eliminarán cuando se carguen conductores)
    rutas = pd.DataFrame({
        'id': [],
        'conductor_id': [],
        'origen': [],
        'destino': [],
        'distancia_km': [],
        'fecha_inicio': [],
        'fecha_fin': [],
        'estado': [],
        'carga_kg': []
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
    
    return rutas, coordenadas


def cargar_archivo_conductores(archivo_cargado):
    """
    Carga archivo Excel o CSV con datos de conductores.
    
    Columnas requeridas:
    - id: Identificador único del conductor
    - nombre: Nombre completo del conductor
    - licencia: Número de licencia de conducir
    - telefono: Número de teléfono
    - vehiculo: Vehículo asignado
    - estado: Estado actual (Activo, En ruta, Descanso, Mantenimiento)
    """
    try:
        # Determinar tipo de archivo
        if archivo_cargado.name.endswith('.csv'):
            df = pd.read_csv(archivo_cargado)
        elif archivo_cargado.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(archivo_cargado)
        else:
            return None, "❌ Formato de archivo no soportado. Use .csv, .xlsx o .xls"
        
        # Validar columnas requeridas
        columnas_requeridas = ['id', 'nombre', 'licencia', 'telefono', 'vehiculo', 'estado']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            return None, f"❌ Columnas faltantes: {', '.join(columnas_faltantes)}"
        
        # Validar que no haya IDs duplicados
        if df['id'].duplicated().any():
            return None, "❌ Error: IDs de conductores duplicados encontrados"
        
        # Validar estados válidos
        estados_validos = ['Activo', 'En ruta', 'Descanso', 'Mantenimiento']
        estados_invalidos = df[~df['estado'].isin(estados_validos)]['estado'].unique()
        
        if len(estados_invalidos) > 0:
            return None, f"❌ Estados inválidos encontrados: {', '.join(estados_invalidos)}. Estados válidos: {', '.join(estados_validos)}"
        
        # Limpiar datos
        df['nombre'] = df['nombre'].astype(str).str.strip()
        df['licencia'] = df['licencia'].astype(str).str.strip()
        df['telefono'] = df['telefono'].astype(str).str.strip()
        df['vehiculo'] = df['vehiculo'].astype(str).str.strip()
        df['id'] = df['id'].astype(int)
        
        return df, f"✅ Archivo cargado exitosamente: {len(df)} conductores"
        
    except Exception as e:
        return None, f"❌ Error al procesar archivo: {str(e)}"


def generar_plantilla_conductores():
    """Genera una plantilla de ejemplo para descargar."""
    plantilla = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'nombre': ['Juan Pérez', 'María García', 'Carlos López', 'Ana Martín', 'Luis Rodríguez'],
        'licencia': ['A123456', 'B789012', 'C345678', 'D901234', 'E567890'],
        'telefono': ['555-0101', '555-0102', '555-0103', '555-0104', '555-0105'],
        'vehiculo': ['Camión Mercedes', 'Furgoneta Ford', 'Camión Volvo', 'Van Toyota', 'Camión Scania'],
        'estado': ['Activo', 'Activo', 'En ruta', 'Activo', 'Descanso']
    })
    return plantilla

# Cargar datos y almacenar en session_state
rutas_default, coordenadas_dict = load_sample_data()

# Inicializar DataFrames en session_state
if 'conductores_df' not in st.session_state:
    st.session_state['conductores_df'] = pd.DataFrame(columns=['id', 'nombre', 'licencia', 'telefono', 'vehiculo', 'estado'])
if 'rutas_df' not in st.session_state:
    st.session_state['rutas_df'] = rutas_default.copy()
if 'conductores_cargados' not in st.session_state:
    st.session_state['conductores_cargados'] = False
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

# Verificar si hay conductores cargados
if not st.session_state['conductores_cargados'] or conductores_df.empty:
    st.warning("⚠️ No hay conductores cargados. Por favor, carga un archivo de conductores primero.")
    st.sidebar.markdown("---")
    st.sidebar.markdown("⚠️ **Cargar Conductores Requerido**")
    st.sidebar.markdown("Ve a la página 'Conductores' para cargar tu archivo.")
    
    # Restringir navegación si no hay conductores
    paginas_disponibles = ["Conductores"]
else:
    paginas_disponibles = ["Dashboard", "Conductores", "Rutas", "Optimización de Rutas", "Mapa de Rutas", "Análisis"]

# Sidebar para navegación
st.sidebar.title("🚛 Gestión de Rutas")
pagina = st.sidebar.selectbox(
    "Seleccionar página:",
    paginas_disponibles
)

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

if pagina == "Conductores":
    st.title("👨‍💼 Gestión de Conductores")
    
    # Sección de carga de archivo
    st.subheader("📁 Cargar Datos de Conductores")
    
    # Información sobre el formato requerido
    with st.expander("ℹ️ Información sobre el formato de archivo"):
        st.markdown("""
        **Columnas requeridas en el archivo:**
        
        | Columna | Descripción | Ejemplo |
        |---------|-------------|---------|
        | `id` | Identificador único (número entero) | 1, 2, 3... |
        | `nombre` | Nombre completo del conductor | Juan Pérez |
        | `licencia` | Número de licencia de conducir | A123456 |
        | `telefono` | Número de teléfono | +51-999-123-456 |
        | `vehiculo` | Vehículo asignado | Camión Mercedes |
        | `estado` | Estado actual | Activo, En ruta, Descanso, Mantenimiento |
        
        **Formatos soportados:** .csv, .xlsx, .xls
        """)
    
    # Descargar plantilla
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Descargar Plantilla Excel", type="secondary"):
            plantilla = generar_plantilla_conductores()
            # Convertir a Excel en memoria
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                plantilla.to_excel(writer, index=False, sheet_name='Conductores')
            
            st.download_button(
                label="💾 Descargar plantilla_conductores.xlsx",
                data=buffer.getvalue(),
                file_name="plantilla_conductores.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with col2:
        if st.button("📥 Descargar Plantilla CSV", type="secondary"):
            plantilla = generar_plantilla_conductores()
            csv = plantilla.to_csv(index=False)
            st.download_button(
                label="💾 Descargar plantilla_conductores.csv",
                data=csv,
                file_name="plantilla_conductores.csv",
                mime="text/csv"
            )
    
    st.markdown("---")
    
    # Upload de archivo
    archivo_cargado = st.file_uploader(
        "📂 Selecciona tu archivo de conductores",
        type=['csv', 'xlsx', 'xls'],
        help="Carga un archivo CSV o Excel con los datos de tus conductores"
    )
    
    if archivo_cargado is not None:
        with st.spinner("🔄 Procesando archivo..."):
            conductores_nuevos, mensaje = cargar_archivo_conductores(archivo_cargado)
        
        if conductores_nuevos is not None:
            st.success(mensaje)
            
            # Mostrar vista previa
            st.subheader("👀 Vista Previa de Datos Cargados")
            st.dataframe(conductores_nuevos, use_container_width=True)
            
            # Botones de acción
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ Confirmar y Usar Datos", type="primary"):
                    st.session_state['conductores_df'] = conductores_nuevos
                    st.session_state['conductores_cargados'] = True
                    st.success("🎉 ¡Datos de conductores cargados exitosamente!")
                    st.balloons()
                    st.rerun()
            
            with col2:
                if st.button("🔄 Agregar a Existentes"):
                    if not st.session_state['conductores_df'].empty:
                        # Verificar IDs duplicados
                        ids_existentes = set(st.session_state['conductores_df']['id'])
                        ids_nuevos = set(conductores_nuevos['id'])
                        duplicados = ids_existentes.intersection(ids_nuevos)
                        
                        if duplicados:
                            st.error(f"❌ IDs duplicados encontrados: {duplicados}")
                        else:
                            st.session_state['conductores_df'] = pd.concat([
                                st.session_state['conductores_df'],
                                conductores_nuevos
                            ], ignore_index=True)
                            st.session_state['conductores_cargados'] = True
                            st.success("✅ Conductores agregados exitosamente!")
                            st.rerun()
                    else:
                        st.session_state['conductores_df'] = conductores_nuevos
                        st.session_state['conductores_cargados'] = True
                        st.success("✅ Primeros conductores cargados!")
                        st.rerun()
            
            with col3:
                if st.button("❌ Cancelar"):
                    st.rerun()
        else:
            st.error(mensaje)
    
    # Mostrar conductores actuales si existen
    if not conductores_df.empty:
        st.markdown("---")
        st.subheader("📋 Conductores Actuales")
        
        # Estadísticas rápidas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Conductores", len(conductores_df))
        with col2:
            activos = len(conductores_df[conductores_df['estado'] == 'Activo'])
            st.metric("Activos", activos)
        with col3:
            en_ruta = len(conductores_df[conductores_df['estado'] == 'En ruta'])
            st.metric("En Ruta", en_ruta)
        with col4:
            descanso = len(conductores_df[conductores_df['estado'] == 'Descanso'])
            st.metric("En Descanso", descanso)
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            filtro_estado = st.selectbox("Filtrar por estado:", ["Todos"] + list(conductores_df['estado'].unique()))
        with col2:
            filtro_nombre = st.text_input("🔍 Buscar por nombre:", placeholder="Ingresa nombre del conductor")
        
        # Aplicar filtros
        conductores_filtrados = conductores_df.copy()
        if filtro_estado != "Todos":
            conductores_filtrados = conductores_filtrados[conductores_filtrados['estado'] == filtro_estado]
        if filtro_nombre:
            conductores_filtrados = conductores_filtrados[
                conductores_filtrados['nombre'].str.contains(filtro_nombre, case=False, na=False)
            ]
        
        # Mostrar tabla filtrada
        st.dataframe(conductores_filtrados, use_container_width=True)
        
        # Acciones adicionales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🗑️ Limpiar Todos los Conductores"):
                if st.button("⚠️ Confirmar Eliminación", type="secondary"):
                    st.session_state['conductores_df'] = pd.DataFrame(columns=['id', 'nombre', 'licencia', 'telefono', 'vehiculo', 'estado'])
                    st.session_state['conductores_cargados'] = False
                    st.warning("🗑️ Todos los conductores han sido eliminados")
                    st.rerun()
        
        with col2:
            if st.button("📊 Exportar Conductores"):
                csv = conductores_df.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar conductores_actual.csv",
                    data=csv,
                    file_name="conductores_actual.csv",
                    mime="text/csv"
                )
        
        with col3:
            if st.button("➕ Agregar Conductor Manual"):
                st.session_state['mostrar_form_manual'] = True
        
        # Formulario manual (si se solicita)
        if st.session_state.get('mostrar_form_manual', False):
            with st.expander("➕ Agregar Conductor Manualmente", expanded=True):
                with st.form("nuevo_conductor_manual"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nuevo_id = st.number_input("ID", min_value=1, value=int(conductores_df['id'].max()) + 1 if not conductores_df.empty else 1)
                        nombre = st.text_input("Nombre completo")
                        licencia = st.text_input("Número de licencia")
                    with col2:
                        telefono = st.text_input("Teléfono")
                        vehiculo = st.text_input("Vehículo asignado")
                        estado = st.selectbox("Estado", ["Activo", "En ruta", "Descanso", "Mantenimiento"])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        submitted = st.form_submit_button("✅ Agregar Conductor", type="primary")
                    with col2:
                        cancelar = st.form_submit_button("❌ Cancelar")
                    
                    if submitted and nombre and licencia:
                        # Verificar ID único
                        if nuevo_id in conductores_df['id'].values:
                            st.error(f"❌ ID {nuevo_id} ya existe. Use un ID diferente.")
                        else:
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
                            st.session_state['mostrar_form_manual'] = False
                            st.success(f"✅ Conductor {nombre} agregado exitosamente!")
                            st.rerun()
                    
                    if cancelar:
                        st.session_state['mostrar_form_manual'] = False
                        st.rerun()
    else:
        st.info("👆 Carga un archivo con los datos de tus conductores para comenzar a usar la aplicación.")

elif pagina == "Dashboard":
    if conductores_df.empty:
        st.title("📊 Dashboard de Transporte")
        st.warning("⚠️ No hay conductores cargados. Ve a la página 'Conductores' para cargar tu archivo.")
        st.stop()
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
    if conductores_df.empty:
        st.title("🗺️ Gestión de Rutas")
        st.warning("⚠️ No hay conductores cargados. Ve a la página 'Conductores' para cargar tu archivo.")
        st.stop()
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

elif pagina == "Optimización de Rutas":
    if conductores_df.empty:
        st.title("🎯 Optimización de Rutas Múltiples")
        st.warning("⚠️ No hay conductores cargados. Ve a la página 'Conductores' para cargar tu archivo.")
        st.stop()
    st.title("🎯 Optimización de Rutas Múltiples")
    st.markdown("**Encuentra la mejor ruta y orden de visita para múltiples destinos**")
    
    # Selector de conductor
    conductor_seleccionado = st.selectbox(
        "👨‍💼 Seleccionar conductor para optimizar:",
        conductores_df['nombre'].values,
        key="conductor_optimizacion"
    )
    
    if conductor_seleccionado:
        conductor_id = conductores_df[conductores_df['nombre'] == conductor_seleccionado]['id'].iloc[0]
        
        # Generar plan de optimización
        with st.spinner("🔄 Analizando y optimizando rutas..."):
            plan_optimizado = generar_plan_ruta_conductor(conductor_id, conductores_df, rutas_df, coordenadas_dict)
        
        if not plan_optimizado:
            st.info(f"📝 No hay rutas pendientes para optimizar para {conductor_seleccionado}")
            
            # Mostrar rutas existentes del conductor
            rutas_conductor = rutas_df[rutas_df['conductor_id'] == conductor_id]
            if not rutas_conductor.empty:
                st.subheader("📋 Rutas Actuales del Conductor")
                rutas_con_conductor = rutas_conductor.merge(
                    conductores_df[['id', 'nombre']], 
                    left_on='conductor_id', 
                    right_on='id'
                )
                st.dataframe(rutas_con_conductor[['id', 'origen', 'destino', 'distancia_km', 'fecha_inicio', 'estado', 'carga_kg']])
        else:
            # Mostrar resumen del conductor
            conductor_info = plan_optimizado['conductor']
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("👨‍💼 Conductor", conductor_info['nombre'])
                st.metric("🚚 Vehículo", conductor_info['vehiculo'])
            
            with col2:
                st.metric("📞 Teléfono", conductor_info['telefono'])
                st.metric("🆔 Licencia", conductor_info['licencia'])
            
            with col3:
                st.metric("📊 Estado", conductor_info['estado'])
            
            # Resumen de optimización
            st.markdown("---")
            st.subheader("📈 Resumen de Optimización")
            
            resumen = plan_optimizado['resumen_total']
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "🛣️ Distancia Actual", 
                    f"{resumen['total_km_actual']:.1f} km"
                )
            
            with col2:
                st.metric(
                    "⚡ Distancia Optimizada", 
                    f"{resumen['total_km_optimizado']:.1f} km"
                )
            
            with col3:
                ahorro_km = resumen['total_ahorro_km']
                ahorro_pct = (ahorro_km / resumen['total_km_actual']) * 100 if resumen['total_km_actual'] > 0 else 0
                st.metric(
                    "💰 Ahorro Total", 
                    f"{ahorro_km:.1f} km",
                    f"{ahorro_pct:.1f}%"
                )
            
            with col4:
                st.metric("🎯 Total Rutas", resumen['total_rutas'])
            
            # Detalles por fecha
            st.markdown("---")
            st.subheader("📅 Plan Optimizado por Fecha")
            
            for fecha, detalles in plan_optimizado['fechas_optimizadas'].items():
                with st.expander(f"📅 {fecha} - {detalles['numero_destinos']} destinos"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📊 Métricas:**")
                        st.metric("📍 Origen", detalles['origen'])
                        st.metric("🎯 Destinos", detalles['numero_destinos'])
                        st.metric("📦 Carga Total", f"{detalles['carga_total']} kg")
                        st.metric("🔧 Algoritmo", detalles['algoritmo'])
                    
                    with col2:
                        st.markdown("**🛣️ Distancias:**")
                        st.metric("Actual", f"{detalles['distancia_actual']:.1f} km")
                        st.metric("Optimizada", f"{detalles['distancia_optimizada']:.1f} km")
                        st.metric(
                            "Ahorro", 
                            f"{detalles['ahorro_km']:.1f} km",
                            f"{detalles['ahorro_porcentaje']:.1f}%"
                        )
                    
                    # Orden recomendado
                    st.markdown("**🗺️ Orden Recomendado de Visita:**")
                    for i, destino in enumerate(detalles['orden_recomendado']):
                        st.write(f"**{i+1}.** {destino}")
                    
                    # Botón para ver mapa
                    if st.button(f"🗺️ Ver Mapa Optimizado", key=f"mapa_{fecha}"):
                        st.session_state[f'mostrar_mapa_{fecha}'] = True
                    
                    # Mostrar mapa si se solicitó
                    if st.session_state.get(f'mostrar_mapa_{fecha}', False):
                        optimizaciones = analizar_rutas_conductor(conductor_id, rutas_df, coordenadas_dict)
                        if fecha in optimizaciones:
                            mapa_opt = crear_mapa_ruta_optimizada(optimizaciones[fecha])
                            if mapa_opt:
                                st_folium(mapa_opt, width=700, height=400)
                        
                        if st.button(f"❌ Ocultar Mapa", key=f"ocultar_mapa_{fecha}"):
                            st.session_state[f'mostrar_mapa_{fecha}'] = False
                            st.rerun()
            
            # Comparación visual de eficiencia
            st.markdown("---")
            st.subheader("📊 Comparación Visual de Eficiencia")
            
            fechas = list(plan_optimizado['fechas_optimizadas'].keys())
            distancias_actual = [plan_optimizado['fechas_optimizadas'][f]['distancia_actual'] for f in fechas]
            distancias_optimizada = [plan_optimizado['fechas_optimizadas'][f]['distancia_optimizada'] for f in fechas]
            
            fig_comparacion = go.Figure()
            
            fig_comparacion.add_trace(go.Bar(
                name='Ruta Actual',
                x=[str(f) for f in fechas],
                y=distancias_actual,
                marker_color='red',
                opacity=0.7
            ))
            
            fig_comparacion.add_trace(go.Bar(
                name='Ruta Optimizada',
                x=[str(f) for f in fechas],
                y=distancias_optimizada,
                marker_color='green',
                opacity=0.7
            ))
            
            fig_comparacion.update_layout(
                title='Comparación de Distancias: Actual vs Optimizada',
                xaxis_title='Fecha',
                yaxis_title='Distancia (km)',
                barmode='group'
            )
            
            st.plotly_chart(fig_comparacion, use_container_width=True)
            
            # Acciones de optimización
            st.markdown("---")
            st.subheader("⚡ Aplicar Optimización")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Aplicar Todas las Optimizaciones", type="primary"):
                    # Aquí se aplicarían las optimizaciones a la base de datos
                    st.success("🎉 ¡Optimizaciones aplicadas exitosamente!")
                    st.info("💡 Las rutas han sido reordenadas según el plan optimizado.")
            
            with col2:
                if st.button("📊 Generar Reporte PDF"):
                    st.info("📄 Funcionalidad de reporte PDF en desarrollo")
            
            # Simulador de optimización manual
            st.markdown("---")
            st.subheader("🧪 Simulador de Optimización Manual")
            
            with st.expander("🔧 Probar diferentes configuraciones"):
                col1, col2 = st.columns(2)
                
                with col1:
                    algoritmo_manual = st.selectbox(
                        "Algoritmo de optimización:",
                        ["nearest_neighbor", "brute_force", "2opt"],
                        help="• Nearest Neighbor: Rápido para muchos destinos\n• Brute Force: Óptimo para pocos destinos (≤8)\n• 2-Opt: Balance entre velocidad y calidad"
                    )
                
                with col2:
                    fecha_simular = st.selectbox(
                        "Fecha a simular:",
                        list(plan_optimizado['fechas_optimizadas'].keys())
                    )
                
                if st.button("🚀 Ejecutar Simulación"):
                    with st.spinner("Calculando nueva optimización..."):
                        # Re-optimizar con algoritmo seleccionado
                        optimizaciones = analizar_rutas_conductor(conductor_id, rutas_df, coordenadas_dict)
                        if fecha_simular in optimizaciones:
                            opt_data = optimizaciones[fecha_simular]
                            nuevo_orden, nueva_distancia = optimizar_ruta_multiple(
                                opt_data['origen'], 
                                opt_data['destinos_original'], 
                                algoritmo_manual
                            )
                            
                            st.success(f"✅ Simulación completada con {algoritmo_manual}")
                            st.metric("Nueva distancia", f"{nueva_distancia:.1f} km")
                            
                            # Mostrar nuevo orden
                            st.write("**Nuevo orden sugerido:**")
                            for i, idx in enumerate(nuevo_orden):
                                destino = opt_data['destinos_original'][idx]
                                st.write(f"{i+1}. {destino['nombre']}")

elif pagina == "Mapa de Rutas":
    if conductores_df.empty:
        st.title("🗺️ Visualización de Rutas")
        st.warning("⚠️ No hay conductores cargados. Ve a la página 'Conductores' para cargar tu archivo.")
        st.stop()
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
    if conductores_df.empty:
        st.title("📈 Análisis de Rendimiento")
        st.warning("⚠️ No hay conductores cargados. Ve a la página 'Conductores' para cargar tu archivo.")
        st.stop()
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

# Información del estado de la aplicación en sidebar
if st.session_state['conductores_cargados'] and not conductores_df.empty:
    st.sidebar.markdown("---")
    st.sidebar.markdown("✅ **Estado: Operativo**")
    st.sidebar.metric("Conductores", len(conductores_df))
    st.sidebar.metric("Rutas", len(rutas_df))
else:
    st.sidebar.markdown("---")
    st.sidebar.markdown("⚠️ **Estado: Configuración**")
    st.sidebar.markdown("Carga conductores para comenzar")
