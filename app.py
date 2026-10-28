"""
================================================================================
INVERNADERO IoT - DASHBOARD DE MONITOREO
PROGRAMA SENATIC 2026 - IEM ARTEMIO MENDOZA
Sensores:   Temperatura, Humedad del aire, Humedad de suelo, Luz, Nivel deposito
Actuadores: Bomba de riego, Ventilador, Iluminacion LED
Flujo:      Wokwi (ESP32) -> ThingSpeak -> GitHub -> Streamlit
================================================================================
"""

import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

# ============================================================================
# 1. CONFIGURACION DE LA PAGINA
# ============================================================================
st.set_page_config(
    page_title="Invernadero IoT",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# 2. CREDENCIALES THINGSPEAK (se leen de Settings -> Secrets en Streamlit)
# ============================================================================
try:
    API_KEY = st.secrets["THINGSPEAK_READ_KEY"]
    CHANNEL_ID = st.secrets["THINGSPEAK_CHANNEL_ID"]
except Exception:
    API_KEY = ""            # canal publico: puede quedar vacio
    CHANNEL_ID = "1234567"  # reemplazar por el Channel ID real

CAMPOS = {
    "field1": "Temperatura",
    "field2": "Humedad",
    "field3": "Suelo",
    "field4": "Luz",
    "field5": "Nivel",
    "field6": "Bomba",
    "field7": "Ventilador",
    "field8": "Iluminacion",
}
SENSORES = ["Temperatura", "Humedad", "Suelo", "Luz", "Nivel"]
ACTUADORES = ["Bomba", "Ventilador", "Iluminacion"]

PAG_INICIO = "🏠 Inicio"
PAG_GRAFICAS = "📈 Gráficas históricas"
PAG_ACTUADORES = "⚙️ Actuadores"
PAG_ALARMAS = "🔔 Alarmas"
PAG_CLIMA = "🌡️ Temperatura y humedad"
PAG_DESCARGAS = "📥 Descargas"


# ============================================================================
# 3. FUNCIONES AUXILIARES
# ============================================================================
@st.cache_data(ttl=20)
def obtener_datos(num_puntos=100):
    """Descarga las ultimas lecturas del canal de ThingSpeak."""
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
    params = {"results": num_puntos}
    if API_KEY:
        params["api_key"] = API_KEY
    try:
        respuesta = requests.get(url, params=params, timeout=10)
        respuesta.raise_for_status()
        feeds = respuesta.json().get("feeds", [])
    except Exception as e:
        st.error(f"No se pudo conectar con ThingSpeak: {e}")
        return None

    if not feeds:
        return pd.DataFrame()

    df = pd.DataFrame(feeds).rename(columns=CAMPOS)
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.tz_convert("America/Bogota")
    for col in SENSORES + ACTUADORES:
        if col not in df:
            df[col] = None
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["Temperatura", "Humedad"]).reset_index(drop=True)


def crear_gauge(valor, minimo, maximo, titulo, unidad, zonas):
    """Indicador semicircular con zonas de color."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        title={"text": titulo, "font": {"size": 18}},
        number={"suffix": unidad, "font": {"size": 40}},
        gauge={
            "axis": {"range": [minimo, maximo], "tickwidth": 1},
            "bar": {"color": "#1f4d2b", "thickness": 0.7},
            "steps": zonas,
        },
    ))
    fig.update_layout(height=280, margin=dict(l=20, r=20, t=60, b=20))
    return fig


def verificar_alarmas(ultima):
    """Revisa la ultima lectura contra los umbrales del cultivo."""
    alertas = []
    t, h = ultima["Temperatura"], ultima["Humedad"]
    s, l, n = ultima["Suelo"], ultima["Luz"], ultima["Nivel"]

    if pd.notna(t) and t < 5:
        alertas.append(("CRITICA", f"Riesgo de helada: {t:.1f} °C"))
    elif pd.notna(t) and t > 32:
        alertas.append(("CRITICA", f"Temperatura muy alta: {t:.1f} °C"))
    elif pd.notna(t) and t > 28:
        alertas.append(("ALTA", f"Temperatura alta: {t:.1f} °C"))
    if pd.notna(h) and h > 85:
        alertas.append(("MEDIA", f"Humedad del aire alta (riesgo de hongos): {h:.1f} %"))
    if pd.notna(s) and s < 30:
        alertas.append(("ALTA", f"Suelo muy seco: {s:.1f} %"))
    if pd.notna(n) and n < 15:
        alertas.append(("CRITICA", f"Depósito casi vacío: {n:.1f} % (riego bloqueado)"))
    if pd.notna(l) and l < 20:
        alertas.append(("MEDIA", f"Luz insuficiente: {l:.1f} %"))
    return alertas


def estado_texto(valor):
    return "ENCENDIDO" if valor == 1 else "APAGADO"


# ============================================================================
# 4. SIDEBAR - NAVEGACION
# ============================================================================
with st.sidebar:
    st.markdown(
        """
        <div style='text-align:center; padding:16px 0;'>
            <div style='font-size:40px;'>🌱</div>
            <div style='font-weight:bold; font-size:18px;'>Invernadero IoT</div>
            <div style='font-size:12px; color:gray;'>Monitoreo y control en tiempo real</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    pagina = st.radio(
        "Navegación",
        [PAG_INICIO, PAG_GRAFICAS, PAG_ACTUADORES, PAG_ALARMAS, PAG_CLIMA, PAG_DESCARGAS],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.subheader("⚙️ Configuración")
    num_puntos = st.slider("Lecturas a mostrar", 10, 500, 100, 10)
    auto_refresh = st.checkbox("⚡ Actualizar cada 20 s", value=False)
    if st.button("🔄 Actualizar ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ============================================================================
# 5. CARGAR DATOS
# ============================================================================
df = obtener_datos(num_puntos)

if df is None or df.empty:
    st.error("❌ No hay datos. Verifique el Channel ID, la Read API Key y que Wokwi esté enviando.")
    st.stop()

ultima = df.iloc[-1]
anterior = df.iloc[-2] if len(df) > 1 else ultima

# ============================================================================
# 6. PAGINA: INICIO
# ============================================================================
if pagina == PAG_INICIO:
    st.markdown("# 🌱 Invernadero IoT")
    st.markdown("Monitoreo del microinvernadero escolar: clima, suelo, luz, depósito de agua y actuadores.")
    st.caption(f"Última lectura: {ultima['created_at'].strftime('%Y-%m-%d %H:%M:%S')} (hora Colombia)")

    st.markdown("### 📊 Sensores")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Temperatura (°C)", f"{ultima['Temperatura']:.1f}",
              f"{ultima['Temperatura'] - anterior['Temperatura']:+.1f}")
    c2.metric("Humedad aire (%)", f"{ultima['Humedad']:.1f}",
              f"{ultima['Humedad'] - anterior['Humedad']:+.1f}")
    c3.metric("Humedad suelo (%)", f"{ultima['Suelo']:.1f}",
              f"{ultima['Suelo'] - anterior['Suelo']:+.1f}")
    c4.metric("Luz (%)", f"{ultima['Luz']:.1f}",
              f"{ultima['Luz'] - anterior['Luz']:+.1f}")
    c5.metric("Depósito (%)", f"{ultima['Nivel']:.1f}",
              f"{ultima['Nivel'] - anterior['Nivel']:+.1f}")

    st.markdown("### ⚙️ Actuadores")
    a1, a2, a3 = st.columns(3)
    a1.metric("💧 Bomba de riego", estado_texto(ultima["Bomba"]))
    a2.metric("🌀 Ventilador", estado_texto(ultima["Ventilador"]))
    a3.metric("💡 Iluminación", estado_texto(ultima["Iluminacion"]))

    st.markdown("---")
    alertas = verificar_alarmas(ultima)
    if alertas:
        st.warning(f"⚠️ Hay {len(alertas)} alarma(s) activa(s). Revise la página de Alarmas.")
    else:
        st.success("✅ Invernadero en condiciones normales")

# ============================================================================
# 7. PAGINA: GRAFICAS HISTORICAS
# ============================================================================
elif pagina == PAG_GRAFICAS:
    st.markdown("# 📈 Gráficas históricas")
    st.markdown("Tendencia de los cinco sensores del invernadero.")

    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=("Temperatura (°C)", "Humedad del aire (%)",
                        "Humedad de suelo (%)", "Luz (%)",
                        "Nivel del depósito (%)", ""),
        vertical_spacing=0.12,
    )
    series = [
        ("Temperatura", "#c2410c", 1, 1),
        ("Humedad", "#2563eb", 1, 2),
        ("Suelo", "#7c4a1e", 2, 1),
        ("Luz", "#ca8a04", 2, 2),
        ("Nivel", "#0e7490", 3, 1),
    ]
    for col, color, fila, columna in series:
        fig.add_trace(
            go.Scatter(x=df["created_at"], y=df[col], name=col,
                       line=dict(color=color, width=2)),
            row=fila, col=columna,
        )
    fig.update_layout(height=900, showlegend=False, template="plotly_white",
                      hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# 8. PAGINA: ACTUADORES
# ============================================================================
elif pagina == PAG_ACTUADORES:
    st.markdown("# ⚙️ Actuadores")
    st.markdown("Estado de la bomba, el ventilador y la iluminación, y el tiempo que estuvieron encendidos.")

    cols = st.columns(3)
    nombres = {"Bomba": "💧 Bomba de riego", "Ventilador": "🌀 Ventilador",
               "Iluminacion": "💡 Iluminación"}
    for col_st, act in zip(cols, ACTUADORES):
        porcentaje = df[act].mean() * 100 if df[act].notna().any() else 0
        col_st.metric(nombres[act], estado_texto(ultima[act]),
                      f"{porcentaje:.0f}% del tiempo encendido", delta_color="off")

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        subplot_titles=[nombres[a] for a in ACTUADORES],
                        vertical_spacing=0.08)
    colores = {"Bomba": "#0e7490", "Ventilador": "#4d7c0f", "Iluminacion": "#ca8a04"}
    for i, act in enumerate(ACTUADORES, start=1):
        fig.add_trace(
            go.Scatter(x=df["created_at"], y=df[act], line_shape="hv", fill="tozeroy",
                       line=dict(color=colores[act], width=2), name=act),
            row=i, col=1,
        )
        fig.update_yaxes(tickvals=[0, 1], ticktext=["OFF", "ON"], range=[-0.1, 1.2],
                         row=i, col=1)
    fig.update_layout(height=600, showlegend=False, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    st.info("La bomba se enciende con suelo < 40 % y se apaga con suelo > 60 %. "
            "Si el depósito baja de 15 %, el riego queda bloqueado para proteger la bomba.")

# ============================================================================
# 9. PAGINA: ALARMAS
# ============================================================================
elif pagina == PAG_ALARMAS:
    st.markdown("# 🔔 Centro de alarmas")
    alertas = verificar_alarmas(ultima)

    if alertas:
        st.warning(f"⚠️ Se detectaron **{len(alertas)}** alarmas activas")
        for tipo, mensaje in alertas:
            if tipo == "CRITICA":
                st.error(f"🚨 {mensaje}")
            elif tipo == "ALTA":
                st.warning(f"⚠️ {mensaje}")
            else:
                st.info(f"ℹ️ {mensaje}")
    else:
        st.success("✅ No hay alarmas activas. Todas las variables están en rango.")

    st.markdown("### 📋 Umbrales configurados")
    df_umbral = pd.DataFrame({
        "Variable": ["Temperatura", "Temperatura", "Temperatura", "Humedad del aire",
                     "Humedad de suelo", "Nivel del depósito", "Luz"],
        "Condición": ["< 5 °C (helada)", "> 32 °C", "> 28 °C", "> 85 %",
                      "< 30 %", "< 15 %", "< 20 %"],
        "Severidad": ["CRÍTICA", "CRÍTICA", "ALTA", "MEDIA", "ALTA", "CRÍTICA", "MEDIA"],
    })
    st.dataframe(df_umbral, use_container_width=True, hide_index=True)

# ============================================================================
# 10. PAGINA: TEMPERATURA Y HUMEDAD
# ============================================================================
elif pagina == PAG_CLIMA:
    st.markdown("# 🌡️ Temperatura y humedad")
    st.markdown("Clima interno del invernadero y humedad del suelo en la última lectura.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.plotly_chart(crear_gauge(
            ultima["Temperatura"], 0, 40, "Temperatura", " °C",
            [{"range": [0, 10], "color": "#bfdbfe"},
             {"range": [10, 18], "color": "#fef3c7"},
             {"range": [18, 26], "color": "#bbf7d0"},
             {"range": [26, 40], "color": "#fecaca"}],
        ), use_container_width=True)
    with c2:
        st.plotly_chart(crear_gauge(
            ultima["Humedad"], 0, 100, "Humedad del aire", " %",
            [{"range": [0, 50], "color": "#fecaca"},
             {"range": [50, 85], "color": "#bbf7d0"},
             {"range": [85, 100], "color": "#fef3c7"}],
        ), use_container_width=True)
    with c3:
        st.plotly_chart(crear_gauge(
            ultima["Suelo"], 0, 100, "Humedad de suelo", " %",
            [{"range": [0, 40], "color": "#fecaca"},
             {"range": [40, 60], "color": "#fef3c7"},
             {"range": [60, 100], "color": "#bbf7d0"}],
        ), use_container_width=True)

    st.markdown("### 📈 Histórico")
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(x=df["created_at"], y=df["Temperatura"], name="Temperatura (°C)",
                                  line=dict(color="#c2410c", width=3), yaxis="y"))
    fig_hist.add_trace(go.Scatter(x=df["created_at"], y=df["Humedad"], name="Humedad aire (%)",
                                  line=dict(color="#2563eb", width=3), yaxis="y2"))
    fig_hist.update_layout(
        yaxis=dict(title=dict(text="Temperatura (°C)", font=dict(color="#c2410c"))),
        yaxis2=dict(title=dict(text="Humedad (%)", font=dict(color="#2563eb")),
                    overlaying="y", side="right"),
        template="plotly_white",
        height=400,
        legend=dict(orientation="h", y=1.12),
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# ============================================================================
# 11. PAGINA: DESCARGAS
# ============================================================================
elif pagina == PAG_DESCARGAS:
    st.markdown("# 📥 Descarga de datos")

    df_export = df[["created_at"] + SENSORES + ACTUADORES].copy()
    df_export["created_at"] = df_export["created_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df_export = df_export.rename(columns={"created_at": "Fecha_Hora"})
    hoy = datetime.now().strftime("%Y%m%d")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📄 CSV", df_export.to_csv(index=False).encode("utf-8"),
                           f"invernadero_{hoy}.csv", "text/csv", use_container_width=True)
    with c2:
        st.download_button("📋 JSON", df_export.to_json(orient="records").encode("utf-8"),
                           f"invernadero_{hoy}.json", "application/json",
                           use_container_width=True)
    with c3:
        st.markdown(f"**{len(df_export)} registros** disponibles")

    st.markdown("### 📋 Vista previa")
    st.dataframe(df_export.sort_values("Fecha_Hora", ascending=False),
                 use_container_width=True, hide_index=True)

# ============================================================================
# 12. PIE DE PAGINA
# ============================================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align:center; color:gray; font-size:12px;'>
        <p>🌱 Invernadero IoT · PROGRAMA SENATIC 2026 - IEM ARTEMIO MENDOZA</p>
        <p>ESP32 + DHT22 + Sensor de suelo + LDR → ThingSpeak → GitHub → Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# 13. ACTUALIZACION AUTOMATICA
# ============================================================================
if auto_refresh:
    time.sleep(20)
    st.cache_data.clear()
    st.rerun()
