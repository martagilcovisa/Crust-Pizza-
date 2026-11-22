"""Dashboard ejecutivo de San Francisco Crust Pizza.

Ejecutar: streamlit run app.py
"""
from __future__ import annotations

import os
import hashlib
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ai_utils import run_ai_analysis
from map_utils import geographic_chart, MAP_FIELDS
from data_utils import (
    by_dimension,
    commercial_insights,
    filter_data,
    kpis,
    load_data,
    monthly_trend,
)

st.set_page_config(
    page_title="Crust Pizza | Inteligencia Comercial",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent / "data"
FILES = {
    "ventas": "San_Francisco_Crust_Pizza_Ventas.xlsx",
    "clientes": "San_Francisco_Crust_Pizza_Clientes.xlsx",
    "productos": "San_Francisco_Crust_Pizza_Productos.xlsx",
}
TEAL = "#A3714F"
DARK = "#493629"
BLUE = "#94775A"
GOLD = "#CA9865"
MUTED = "#8B7868"

st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    html, body, [class*="css"], [data-testid="stApp"] {font-family: 'DM Sans', sans-serif;}
    [data-testid="stAppViewContainer"] { background: #F7F3ED; }
    .block-container {padding-top: 1.25rem; padding-bottom: 2.8rem; max-width: 1450px;}
    [data-testid="stSidebar"] {background-color: #FFFDFA; border-right: 1px solid #E8DED3;}
    [data-testid="stSidebar"] .block-container {padding-top: 2rem;}
    h1,h2,h3 {color:#493629; font-family: 'Manrope', sans-serif; letter-spacing:-.025em;}
    [data-testid="stMetric"] {background:white; padding:1rem 1.15rem; border:1px solid #EAE0D5;
       border-radius:15px; box-shadow: 0 4px 18px rgba(22,54,78,.035); min-height:118px;}
    [data-testid="stMetricLabel"] {font-weight:600;color:#8F7D6E;}
    [data-testid="stMetricValue"] {color:#3F3025; font-family:'Manrope',sans-serif; font-weight:800; font-size:clamp(1.45rem,2.1vw,2rem);}
    [data-testid="stTabs"] button {font-family:'DM Sans',sans-serif; font-weight:600;}
    [data-testid="stTabs"] button[aria-selected="true"] {color:#A3714F;}
    .hero {background:linear-gradient(110deg,#5C4636,#9B7758); color:white; border-radius:19px;
         padding:22px 27px; margin:0 0 18px 0; position:relative; overflow:hidden;}
    .hero:after {content:'◌';position:absolute;right:26px;top:-87px;font-size:240px;opacity:.08;}
    .hero .eyebrow {font-size:.73rem;font-weight:700;letter-spacing:.18em;opacity:.72;text-transform:uppercase;}
    .hero h1 {color:white; font-size:clamp(1.55rem,2.6vw,2.35rem); margin:.32rem 0 .3rem;}
    .hero .sub {color:#F5E4D0; font-size:.91rem; margin:0;}
    .sidebrand {font-family:'Manrope',sans-serif;font-size:1.22rem;font-weight:800;color:#493629;margin-bottom:0;}
    .sidecaption {color:#8B7868;font-size:.78rem; margin-bottom:1.3rem;}
    .sectiontag {color:#A17352;font-size:.77rem;letter-spacing:.11em;text-transform:uppercase;font-weight:800;margin-top:12px;}
    .micro {color:#958172;font-size:.78rem;}
    .insight {background:#fff; border:1px solid #EAE0D5; border-left:4px solid #AE7855; border-radius:12px;
       padding:13px 16px; margin:12px 0; box-shadow:0 3px 12px rgba(0,0,0,.025);}
    .insight strong {color:#4D392B;}
    .insight p {margin:.35rem 0;font-size:.91rem;}
    .insight small {color:#826B5A;}
    .labelchip {display:inline-block;padding:5px 10px;border:1px solid #E4D6C6;background:#F1E7DA;
         color:#80583E;font-weight:700;border-radius:50px;font-size:.75rem;}
    [data-testid="stDataFrame"] {border:1px solid #E9DED1; border-radius:12px;overflow:hidden;}
    </style>""",
    unsafe_allow_html=True,
)


def money(value: float, decimals: int = 0) -> str:
    """Miles con punto y decimales con coma, respetando USD."""
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".") + " $"


def integer(value: int | float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def percentage(value: float) -> str:
    return f"{value:.2f}".replace(".", ",") + " %"


def prettify_chart(fig: go.Figure, height: int = 335) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=12, r=15, t=28, b=15),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, Arial", color=DARK, size=12),
        showlegend=False, hoverlabel=dict(bgcolor="white", font_color=DARK),
    )
    fig.update_xaxes(showgrid=False, linecolor="#E9DFD4", tickfont_color="#907D6C")
    fig.update_yaxes(gridcolor="#F1E7DD", zeroline=False, tickfont_color="#907D6C")
    return fig


def bar_chart(frame: pd.DataFrame, category: str, metric: str, n: int | None = None,
              horizontal: bool = True, color: str = TEAL, height: int = 345) -> go.Figure:
    frame = frame.sort_values(metric, ascending=False)
    if n:
        frame = frame.head(n)
    if horizontal:
        frame = frame.iloc[::-1]
        fig = px.bar(frame, x=metric, y=category, orientation="h", text=metric)
        fig.update_traces(marker_color=color, texttemplate="%{text:,.0f}", textposition="outside",
                          cliponaxis=False, hovertemplate="%{y}<br>%{x:,.2f}<extra></extra>")
        fig.update_xaxes(title=None, range=[0, float(frame[metric].max()) * 1.24 if not frame.empty else 1])
        fig.update_yaxes(title=None)
    else:
        fig = px.bar(frame, x=category, y=metric, text=metric)
        fig.update_traces(marker_color=color, texttemplate="%{text:,.0f}", textposition="outside",cliponaxis=False)
        fig.update_xaxes(title=None)
        fig.update_yaxes(title=None)
    return prettify_chart(fig, height)


def table_with_format(df: pd.DataFrame, map_cols: dict[str, str]) -> None:
    out = df.rename(columns=map_cols).copy()
    numeric_config = {}
    for field in ("Ventas netas", "Utilidad bruta", "Costes", "Ticket medio"):
        if field in out:
            numeric_config[field] = st.column_config.NumberColumn(field, format="$%.2f")
    if "Margen (%)" in out:
        numeric_config["Margen (%)"] = st.column_config.NumberColumn("Margen (%)", format="%.2f%%")
    for field in ("Transacciones", "Unidades", "Clientes"):
        if field in out:
            numeric_config[field] = st.column_config.NumberColumn(field, format="%d")
    st.dataframe(out, hide_index=True, use_container_width=True, column_config=numeric_config)


@st.cache_data(show_spinner=False, max_entries=5)
def get_joined(ventas_bytes: bytes, clientes_bytes: bytes, productos_bytes: bytes):
    return load_data(ventas_bytes, clientes_bytes, productos_bytes)


with st.sidebar:
    st.markdown('<div class="sidebrand">🍕 Crust Pizza</div><div class="sidecaption">Business Intelligence · Dirección Comercial</div>', unsafe_allow_html=True)
    with st.expander("📤 Gestión de datos · Subir nuevos Excel", expanded=True):
        st.caption("Sube una nueva base de ventas, clientes o productos. Todos los indicadores se recalculan. Los cambios duran solo esta sesión.")
        new_ventas = st.file_uploader("Nueva base de ventas", type="xlsx", key="ventas_xlsx")
        new_clientes = st.file_uploader("Nueva base de clientes", type="xlsx", key="clientes_xlsx")
        new_productos = st.file_uploader("Nueva base de productos", type="xlsx", key="productos_xlsx")
        st.caption("Se exige conservar los identificadores y las columnas esenciales.")

try:
    file_bytes = {
        "ventas": new_ventas.getvalue() if new_ventas is not None else (BASE / FILES["ventas"]).read_bytes(),
        "clientes": new_clientes.getvalue() if new_clientes is not None else (BASE / FILES["clientes"]).read_bytes(),
        "productos": new_productos.getvalue() if new_productos is not None else (BASE / FILES["productos"]).read_bytes(),
    }
    raw, quality = get_joined(file_bytes["ventas"], file_bytes["clientes"], file_bytes["productos"])
except (OSError, ValueError) as error:
    st.error(f"No se pudieron cargar las bases de datos: {error}")
    st.info("Revisa los Excel cargados. Los archivos originales deben estar en la carpeta data/.")
    st.stop()

# Restablecer los filtros cuando cambia cualquier Excel, para que un periodo
# anterior no bloquee una base nueva con otras fechas o ciudades.
dataset_fingerprint = hashlib.sha256(b"".join(
    hashlib.sha256(file_bytes[name]).digest() for name in ("ventas", "clientes", "productos")
)).hexdigest()
if st.session_state.get("_dataset_fingerprint") != dataset_fingerprint:
    for widget_key in ("rango_fechas", "filtro_ciudad", "filtro_sucursal", "filtro_segmento", "filtro_producto"):
        st.session_state.pop(widget_key, None)
    st.session_state["_dataset_fingerprint"] = dataset_fingerprint


def seleccionar_ciudad(nombre: str) -> None:
    """Permite cambiar de ciudad sin eliminar los otros puntos del mapa."""
    actual = st.session_state.get("filtro_ciudad", [])
    st.session_state["filtro_ciudad"] = [] if actual == [nombre] else [nombre]
    # Un cambio de ciudad deja de aplicar sucursales de otra ciudad.
    st.session_state["filtro_sucursal"] = []


with st.sidebar:
    st.markdown('<div class="sectiontag">Filtros de análisis</div>', unsafe_allow_html=True)
    range_dates = st.date_input(
        "Periodo de ventas", value=(quality["fecha_inicial"], quality["fecha_final"]),
        min_value=quality["fecha_inicial"], max_value=quality["fecha_final"],
        format="DD/MM/YYYY", key="rango_fechas",
    )
    cities = st.multiselect("Ciudad", sorted(raw["Ciudad"].dropna().unique()), placeholder="Todas las ciudades", key="filtro_ciudad")
    scoped_stores = sorted(raw[raw["Ciudad"].isin(cities)]["Sucursal"].unique()) if cities else sorted(raw["Sucursal"].unique())
    stores = st.multiselect("Sucursal", scoped_stores, placeholder="Todas las sucursales", key="filtro_sucursal")
    segments = st.multiselect("Segmento de cliente", sorted(raw["Segmento"].unique()), placeholder="Todos los segmentos", key="filtro_segmento")
    product_names = raw[["ProductoID", "ProductoEtiqueta"]].drop_duplicates().set_index("ProductoID")["ProductoEtiqueta"].to_dict()
    products = st.multiselect("Producto", sorted(product_names), format_func=lambda p: product_names.get(p, p),placeholder="Todos los productos", key="filtro_producto")
    st.caption("Sin selección = todas las opciones. Los filtros se combinan entre sí.")
    st.divider()
    st.markdown(f"<span class='labelchip'>● Fuente: {'actualizada' if any([new_ventas, new_clientes, new_productos]) else 'Excel original'}</span>", unsafe_allow_html=True)
    st.caption("Datos históricos de 2024–2025 · Importes en USD")

if not isinstance(range_dates, tuple) or len(range_dates) != 2:
    st.warning("Selecciona una fecha inicial y otra final para continuar.")
    st.stop()
if range_dates[0] > range_dates[1]:
    st.warning("La fecha inicial no puede ser posterior a la fecha final.")
    st.stop()
filtered = filter_data(raw, range_dates[0], range_dates[1], cities, stores, segments, products)

st.markdown("""<div class="hero">
  <div class="eyebrow">Commercial intelligence / Executive view</div>
  <h1>San Francisco Crust Pizza</h1>
  <p class="sub">Un negocio más inteligente empieza por decisiones basadas en datos.</p>
</div>""", unsafe_allow_html=True)

st.markdown(f"**Periodo seleccionado:** {range_dates[0].strftime('%d/%m/%Y')} – {range_dates[1].strftime('%d/%m/%Y')} &nbsp; · &nbsp; **Registros:** {integer(len(filtered))} de {integer(len(raw))}")

if filtered.empty:
    st.warning("No hay operaciones con esta combinación de filtros. Amplía el periodo o cambia las selecciones.")
    st.stop()

metrics = kpis(filtered)
c1, c2, c3 = st.columns(3)
c1.metric("Ventas totales", money(metrics["ventas"], 2))
c2.metric("Utilidad bruta", money(metrics["utilidad"], 2))
c3.metric("Margen bruto", percentage(metrics["margen"]))
c4, c5, c6 = st.columns(3)
c4.metric("Ticket promedio", money(metrics["ticket"], 2))
c5.metric("Clientes únicos", integer(metrics["clientes"]))
c6.metric("Transacciones", integer(metrics["transacciones"]))

st.caption("Utilidad bruta = ventas netas − costes directos. Margen bruto = utilidad bruta / ventas netas. Ticket = ventas netas / transacciones distintas.")

tabs = st.tabs(["📈 Resumen", "🗺️ Análisis geográfico", "🏬 Sucursales", "🍕 Productos", "👥 Clientes y canales", "✦ Asistente IA", "🗂️ Datos y método"])

with tabs[0]:
    st.subheader("Radiografía comercial")
    trend = monthly_trend(filtered)
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=trend["MesAnalisis"], y=trend["VentaNeta"], mode="lines+markers", name="Ventas",
        line=dict(color=TEAL, width=3), marker=dict(size=5), fill="tozeroy", fillcolor="rgba(163,113,79,.09)",
        hovertemplate="%{x|%b %Y}<br>Ventas: $%{y:,.2f}<extra></extra>"))
    fig_trend.add_trace(go.Scatter(x=trend["MesAnalisis"], y=trend["UtilidadBruta"], mode="lines", name="Utilidad",
        line=dict(color=GOLD, width=2, dash="dot"), hovertemplate="%{x|%b %Y}<br>Utilidad: $%{y:,.2f}<extra></extra>"))
    fig_trend = prettify_chart(fig_trend, 350)
    fig_trend.update_layout(showlegend=True, legend=dict(orientation="h", y=1.13, x=0))
    fig_trend.update_yaxes(title="USD", tickprefix="$", separatethousands=True)
    st.plotly_chart(fig_trend, use_container_width=True, key="trend")

    st.markdown("#### Actividad geográfica · Estados Unidos")
    st.caption("Texas concentra todas las ciudades del caso. El mapa responde a los filtros activos.")
    overview_col, overview_notes = st.columns([1.8, 1])
    with overview_col:
        st.plotly_chart(geographic_chart(by_dimension(filtered, 'Ciudad'), 'Ventas netas'), use_container_width=True, key='geo_overview')
    with overview_notes:
        st.markdown("**Ventas de las cuatro ciudades**")
        st.plotly_chart(bar_chart(by_dimension(filtered,'Ciudad'),'Ciudad','VentaNeta',height=300), use_container_width=True, key='geo_overview_ranking')
        st.caption("Los círculos señalan centros urbanos aproximados, no ubicaciones verificadas de sucursales.")

    left, right = st.columns(2)
    with left:
        st.markdown("**Ventas por ciudad**")
        st.plotly_chart(bar_chart(by_dimension(filtered,"Ciudad"),"Ciudad","VentaNeta",height=310), use_container_width=True, key="cities")
    with right:
        st.markdown("**Utilidad bruta por sucursal**")
        st.plotly_chart(bar_chart(by_dimension(filtered,"Sucursal"),"Sucursal","UtilidadBruta",height=310), use_container_width=True, key="stores")
    left, right = st.columns(2)
    with left:
        st.markdown("**Productos más vendidos · unidades**")
        st.plotly_chart(bar_chart(by_dimension(filtered,"ProductoEtiqueta"),"ProductoEtiqueta","Cantidad",n=6,color=BLUE,height=325),use_container_width=True,key="topunits")
    with right:
        st.markdown("**Ventas por segmento de cliente**")
        seg = by_dimension(filtered,"Segmento")
        pie = px.pie(seg, names="Segmento", values="VentaNeta", hole=.66,
                     color_discrete_sequence=[TEAL,DARK,BLUE,GOLD])
        pie.update_traces(textposition="outside", textinfo="percent+label", hovertemplate="%{label}<br>$%{value:,.2f}<extra></extra>")
        st.plotly_chart(prettify_chart(pie, 325),use_container_width=True,key="segments_pie")

with tabs[1]:
    st.subheader("Análisis geográfico · Estados Unidos y Texas")
    st.caption("Estados Unidos ofrece contexto territorial; Texas permite comparar los resultados por ciudad. Las demás zonas no tienen operaciones registradas en los archivos disponibles.")
    st.markdown("**Selecciona una ciudad (pulsar de nuevo para mostrar todas):**")
    available_cities = [c for c in ["Dallas", "Houston", "Austin", "San Antonio"] if c in raw["Ciudad"].unique()]
    if available_cities:
        city_buttons = st.columns(len(available_cities))
        for column, city_name in zip(city_buttons, available_cities):
            with column:
                st.button(
                    city_name + (" ✓" if cities == [city_name] else ""),
                    on_click=seleccionar_ciudad, args=(city_name,),
                    use_container_width=True,
                    type="primary" if cities == [city_name] else "secondary",
                    key="geo_city_" + city_name.replace(" ", "_"),
                )
    st.caption("Al cambiar de ciudad, se recalculan las métricas y los mapas. Los puntos del mapa permiten ver detalles al pasar el cursor; usa los botones para cambiar de ciudad.")
    map_metric = st.selectbox("Indicador representado", list(MAP_FIELDS), key="map_metric")
    by_city = by_dimension(filtered, "Ciudad")
    usa_col, texas_col = st.columns(2)
    with usa_col:
        st.markdown("**Estados Unidos · Texas destacado**")
        st.plotly_chart(geographic_chart(by_city, map_metric),use_container_width=True,key='us_map')
    with texas_col:
        st.markdown("**Texas · Dallas, Houston, Austin y San Antonio**")
        st.plotly_chart(geographic_chart(by_city,map_metric,texas_only=True),use_container_width=True,key='texas_map')
    st.markdown("**Ranking de ciudades según el indicador**")
    st.plotly_chart(bar_chart(by_city,'Ciudad',MAP_FIELDS[map_metric],height=295),use_container_width=True,key='city_rank_metric')
    table_with_format(by_city[["Ciudad","VentaNeta","UtilidadBruta","MargenPct","TicketMedio","Transacciones","Clientes"]],
        {"Ciudad":"Ciudad","VentaNeta":"Ventas netas","UtilidadBruta":"Utilidad bruta","MargenPct":"Margen (%)","TicketMedio":"Ticket medio","Transacciones":"Transacciones","Clientes":"Clientes"})
    st.info("Los puntos se sitúan en centros aproximados de ciudad, no en las direcciones de las ocho sucursales. Una ciudad nueva cargada desde Excel necesita coordenadas para aparecer en el mapa, aunque sí se incluye en los indicadores y tablas.")

with tabs[2]:
    st.subheader("Comparación de sucursales")
    st.caption("Puedes ordenar la tabla y contrastar volumen, utilidad, margen y ticket medio. Mayor facturación no implica mayor rentabilidad.")
    store_data = by_dimension(filtered, "Sucursal").sort_values("UtilidadBruta", ascending=False)
    if len(store_data) >= 2:
        best, worst = store_data.iloc[0], store_data.iloc[-1]
        a, b = st.columns(2)
        a.success(f"Mayor utilidad bruta: **{best['Sucursal']}** · {money(best['UtilidadBruta'],2)}")
        b.warning(f"Menor utilidad bruta: **{worst['Sucursal']}** · {money(worst['UtilidadBruta'],2)}")
    comparison = st.selectbox("Comparar sucursales por", ["Utilidad bruta", "Ventas netas", "Margen (%)", "Ticket medio", "Transacciones"], key="store_metric")
    fields = {"Utilidad bruta":"UtilidadBruta","Ventas netas":"VentaNeta","Margen (%)":"MargenPct","Ticket medio":"TicketMedio","Transacciones":"Transacciones"}
    st.plotly_chart(bar_chart(store_data, "Sucursal", fields[comparison], color=TEAL, height=390), use_container_width=True, key="branch_compare")
    table_with_format(store_data[["Sucursal","VentaNeta","CostoTotal","UtilidadBruta","MargenPct","TicketMedio","Transacciones","Clientes"]],
        {"Sucursal":"Sucursal","VentaNeta":"Ventas netas","CostoTotal":"Costes","UtilidadBruta":"Utilidad bruta","MargenPct":"Margen (%)","TicketMedio":"Ticket medio","Transacciones":"Transacciones","Clientes":"Clientes"})

with tabs[3]:
    st.subheader("Rentabilidad del catálogo")
    products_df = by_dimension(filtered, "ProductoEtiqueta").sort_values("UtilidadBruta", ascending=False)
    c1,c2=st.columns(2)
    with c1:
        st.markdown("**Top 10 por contribución a la utilidad bruta**")
        st.plotly_chart(bar_chart(products_df, "ProductoEtiqueta", "UtilidadBruta", n=10, height=425), use_container_width=True, key="prodprofit")
    with c2:
        st.markdown("**Top 10 por cantidad vendida**")
        st.plotly_chart(bar_chart(products_df, "ProductoEtiqueta", "Cantidad", n=10, color=BLUE, height=425), use_container_width=True, key="prodvol")
    st.markdown("**Productos con menor margen bruto (muestra mínima seleccionable)**")
    min_tx = st.slider("Mínimo de transacciones del producto", min_value=1, max_value=max(1,int(products_df["Transacciones"].max())),value=min(100,max(1,int(products_df["Transacciones"].max()))), key="prod_min_tx")
    reviewed = products_df[products_df["Transacciones"]>=min_tx].sort_values("MargenPct",ascending=True)
    table_with_format(reviewed[["ProductoEtiqueta","VentaNeta","UtilidadBruta","MargenPct","Cantidad","Transacciones"]],
        {"ProductoEtiqueta":"Producto","VentaNeta":"Ventas netas","UtilidadBruta":"Utilidad bruta","MargenPct":"Margen (%)","Cantidad":"Unidades","Transacciones":"Transacciones"})
    st.caption("Las valoraciones de margen tienen en cuenta el volumen para evitar comparar productos con muestras muy pequeñas.")

with tabs[4]:
    st.subheader("Clientes, segmentos y canales de venta")
    segment_data = by_dimension(filtered, "Segmento").sort_values("VentaNeta", ascending=False)
    left,right=st.columns(2)
    with left:
        st.markdown("**Contribución por segmento**")
        st.plotly_chart(bar_chart(segment_data, "Segmento", "VentaNeta",height=325), use_container_width=True,key="segcontrib")
    with right:
        st.markdown("**Ticket promedio por segmento**")
        st.plotly_chart(bar_chart(segment_data, "Segmento", "TicketMedio",color=BLUE,height=325), use_container_width=True,key="segticket")
    table_with_format(segment_data[["Segmento","VentaNeta","UtilidadBruta","MargenPct","TicketMedio","Transacciones","Clientes"]],
        {"Segmento":"Segmento","VentaNeta":"Ventas netas","UtilidadBruta":"Utilidad bruta","MargenPct":"Margen (%)","TicketMedio":"Ticket medio","Transacciones":"Transacciones","Clientes":"Clientes"})
    if "Canal" in filtered:
        st.markdown("**Rendimiento por canal**")
        channel_data = by_dimension(filtered,"Canal").sort_values("VentaNeta",ascending=False)
        left,right=st.columns(2)
        with left:
            st.plotly_chart(bar_chart(channel_data, "Canal", "VentaNeta",color=GOLD,height=310),use_container_width=True,key="channelplot")
        with right:
            table_with_format(channel_data[["Canal","VentaNeta","UtilidadBruta","MargenPct","Transacciones"]],
                {"Canal":"Canal","VentaNeta":"Ventas netas","UtilidadBruta":"Utilidad bruta","MargenPct":"Margen (%)","Transacciones":"Transacciones"})

with tabs[5]:
    st.subheader("Asistente de inteligencia comercial")
    st.write("Convierte las métricas del periodo filtrado en recomendaciones argumentadas. El sistema distingue los hallazgos automáticos de la **IA generativa**.")
    st.markdown("#### Hallazgos automáticos verificables")
    for item in commercial_insights(filtered):
        st.markdown(f"<div class='insight'><strong>{item['titulo']}</strong><p>{item['evidencia']}</p><small><b>Acción posible:</b> {item['accion']}</small></div>", unsafe_allow_html=True)
    st.divider()
    st.markdown("#### Pregunta al asistente con IA generativa")
    st.caption("Para activar respuestas generadas por un modelo de IA hace falta una clave API. Nunca se incluyen datos personales de clientes: solo se envían resultados agregados.")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", api_key)
    except Exception:
        pass
    if not api_key:
        api_key = st.text_input("Clave API de OpenAI (opcional; solo durante tu sesión)", type="password",key="openai_key",help="No se guarda en los Excel ni en el proyecto.")
    question = st.text_area("¿Qué quieres analizar?",value="Propón cinco decisiones comerciales, ordenadas por prioridad, apoyándote en los datos del periodo seleccionado. Incluye riesgos y cómo medir resultados.",height=120,key="ia_question")
    if st.button("✦ Generar recomendaciones con IA", type="primary", disabled=not bool(api_key), key="generate_ai"):
        try:
            with st.spinner("Analizando las métricas agregadas..."):
                answer = run_ai_analysis(filtered, question, api_key)
            st.markdown("### Recomendaciones de la IA")
            st.write(answer)
            st.warning("**Evaluación crítica obligatoria:** comprueba que cada cifra aparece en el dashboard. La utilidad bruta no descuenta alquileres, personal ni marketing; una propuesta no demuestra causalidad por sí sola.")
        except Exception as exc:
            st.error(f"La conexión con el modelo de IA no ha funcionado. Revisa la clave, la conexión y el acceso al modelo. Detalle: {type(exc).__name__}: {exc}")
    if not api_key:
        st.info("La parte automática de hallazgos funciona sin credenciales. Para utilizar la IA generativa introduce una clave API o configúrala en los secretos del despliegue.")

with tabs[6]:
    st.subheader("Datos, actualización y transparencia")
    st.write("Fuente principal: fichero de ventas; las otras dos tablas se relacionan por **ClienteID** y **ProductoID**. Los precios y costes históricos de cada venta prevalecen sobre los del catálogo.")
    a,b,c = st.columns(3)
    a.metric("Registros de ventas",integer(quality["registros_ventas"]))
    b.metric("Clientes del catálogo",integer(quality["clientes_catalogo"]))
    c.metric("Productos del catálogo",integer(quality["productos_catalogo"]))
    checks = [
        ("Ventas sin cliente asociado",quality["sin_cliente"]),
        ("Ventas sin producto asociado",quality["sin_producto"]),
        ("Identificadores de venta repetidos",quality["transacciones_repetidas"]),
        ("Discrepancias en utilidad bruta histórica",quality["utilidad_no_cuadra"]),
    ]
    for label, count in checks:
        (st.success if count == 0 else st.warning)(f"{label}: **{integer(count)}**")
    with st.expander("Fórmulas y definiciones de indicadores"):
        st.markdown("""- **Ventas totales:** suma de `VentaNeta` de las operaciones filtradas.
- **Costes directos:** suma de `CostoTotal` de esas operaciones.
- **Utilidad bruta:** ventas totales menos costes directos.
- **Margen bruto:** (utilidad bruta / ventas totales) × 100, ponderado por ventas.
- **Ticket promedio:** ventas totales / número de `VentaID` únicos.
- **Clientes únicos:** número de `ClienteID` diferentes con compra.
- **Transacciones:** número de `VentaID` diferentes, no unidades vendidas.
- **Productos más vendidos:** unidades vendidas (`Cantidad`) por producto.

**Limitación:** la utilidad bruta no equivale a beneficio neto, porque no incluye todos los gastos generales y de estructura.""")
    st.markdown("#### Exportar resultados filtrados")
    export = filtered[["VentaID","Fecha","Ciudad","Sucursal","ClienteID","ProductoID","Producto","Segmento","Cantidad","VentaNeta","CostoTotal","UtilidadBruta"]].copy()
    export["Fecha"] = export["Fecha"].dt.strftime("%Y-%m-%d")
    st.download_button("⬇️ Descargar ventas filtradas (CSV)",data=export.to_csv(index=False).encode("utf-8-sig"),file_name="crust_pizza_ventas_filtradas.csv",mime="text/csv",key="exportcsv")
    st.dataframe(export.head(50),hide_index=True,use_container_width=True)
    st.caption("Vista preliminar de 50 filas. El CSV incluye todas las operaciones filtradas.")

st.markdown("<p style='text-align:center;color:#A08A79;font-size:.76rem;margin-top:36px'>CRUST PIZZA • BUSINESS INTELLIGENCE • Proyecto académico | Datos procedentes de los Excel facilitados</p>",unsafe_allow_html=True)
