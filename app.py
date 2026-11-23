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
    api_key = os.environ.get("GEMINI_API_KEY", "")
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", api_key)
    except Exception:
        pass
    if not api_key:
        api_key = st.text_input("Clave API de Gemini (opcional; solo durante tu sesión)", type="password",key="gemini_key",help="No se guarda en los Excel ni en el proyecto.")
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
