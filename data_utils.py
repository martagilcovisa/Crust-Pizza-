"""Capa de datos y métricas para San Francisco Crust Pizza.

Principio de cálculo: los importes históricos de cada transacción prevalecen
sobre los precios de referencia vigentes en el catálogo de productos.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


REQUIRED_VENTAS = {
    "VentaID", "Fecha", "Ciudad", "Sucursal", "ClienteID", "ProductoID",
    "Cantidad", "VentaNeta", "CostoTotal",
}
REQUIRED_CLIENTES = {"ClienteID", "Segmento"}
REQUIRED_PRODUCTOS = {"ProductoID", "Producto"}


def _read_excel(content: bytes, label: str) -> pd.DataFrame:
    try:
        data = pd.read_excel(BytesIO(content), engine="openpyxl")
    except Exception as exc:
        raise ValueError(f"No se pudo abrir el Excel de {label}: {exc}") from exc
    data.columns = data.columns.map(lambda x: str(x).strip())
    if data.empty:
        raise ValueError(f"El archivo de {label} no contiene registros.")
    return data


def _require_columns(df: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Al archivo de {label} le faltan columnas: {', '.join(missing)}.")


def _parse_excel_dates(series: pd.Series) -> pd.Series:
    # Algunos Excel de reemplazo guardan fechas como números de serie.
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_datetime(series, unit="D", origin="1899-12-30", errors="coerce")
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def load_data(ventas_bytes: bytes, clientes_bytes: bytes, productos_bytes: bytes) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Validar, relacionar tablas y crear columnas auxiliares; no elimina ventas."""
    ventas = _read_excel(ventas_bytes, "ventas")
    clientes = _read_excel(clientes_bytes, "clientes")
    productos = _read_excel(productos_bytes, "productos")
    _require_columns(ventas, REQUIRED_VENTAS, "ventas")
    _require_columns(clientes, REQUIRED_CLIENTES, "clientes")
    _require_columns(productos, REQUIRED_PRODUCTOS, "productos")

    for df, id_col, name in [(clientes, "ClienteID", "clientes"), (productos, "ProductoID", "productos")]:
        if df[id_col].isna().any() or df[id_col].astype(str).str.strip().eq("").any():
            raise ValueError(f"En {name} hay identificadores vacíos: revísalos en Excel.")
        if df[id_col].astype(str).duplicated().any():
            raise ValueError(f"En {name} hay identificadores repetidos: la unión duplicaría ventas.")
        df[id_col] = df[id_col].astype(str).str.strip()

    for col in ["VentaID", "Ciudad", "Sucursal", "ClienteID", "ProductoID"]:
        if ventas[col].isna().any() or ventas[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"La columna '{col}' de ventas contiene valores vacíos.")
        ventas[col] = ventas[col].astype(str).str.strip()

    ventas["Fecha"] = _parse_excel_dates(ventas["Fecha"])
    if ventas["Fecha"].isna().any():
        raise ValueError(f"Hay {int(ventas['Fecha'].isna().sum())} fechas de ventas no válidas.")

    for field in ["Cantidad", "VentaNeta", "CostoTotal"]:
        ventas[field] = pd.to_numeric(ventas[field], errors="coerce")
        if ventas[field].isna().any():
            raise ValueError(f"Hay {int(ventas[field].isna().sum())} valores no numéricos en '{field}'.")

    if (ventas["Cantidad"] <= 0).any():
        raise ValueError("Hay cantidades cero o negativas. Revisa si son devoluciones y cómo deben tratarse.")

    clientes["Segmento"] = clientes["Segmento"].fillna("Sin clasificar").astype(str).str.strip().replace("", "Sin clasificar")
    productos["Producto"] = productos["Producto"].fillna("Producto sin nombre").astype(str).str.strip()
    if "Categoria" not in productos:
        productos["Categoria"] = "Sin categoría"
    if "Tamaño" not in productos:
        productos["Tamaño"] = ""
    productos["Tamaño"] = productos["Tamaño"].fillna("").astype(str).str.strip()
    productos["Categoria"] = productos["Categoria"].fillna("Sin categoría").astype(str).str.strip()

    if "UtilidadBruta" in ventas:
        utilidad_original = pd.to_numeric(ventas["UtilidadBruta"], errors="coerce")
        discrepancias = int(((utilidad_original - (ventas["VentaNeta"] - ventas["CostoTotal"])).abs() > 0.025).sum())
    else:
        discrepancias = 0
    # Fórmula de referencia, garantizando coherencia entre los KPI y las gráficas.
    ventas["UtilidadBruta"] = ventas["VentaNeta"] - ventas["CostoTotal"]

    ventas["ProductoID"] = ventas["ProductoID"].astype(str)
    ventas["ClienteID"] = ventas["ClienteID"].astype(str)
    ids_sin_cliente = int((~ventas["ClienteID"].isin(clientes["ClienteID"])).sum())
    ids_sin_producto = int((~ventas["ProductoID"].isin(productos["ProductoID"])).sum())

    joined = ventas.merge(clientes[["ClienteID", "Segmento"]], on="ClienteID", how="left", validate="m:1")
    joined = joined.merge(
        productos[["ProductoID", "Producto", "Categoria", "Tamaño"]],
        on="ProductoID", how="left", validate="m:1",
    )
    joined["Segmento"] = joined["Segmento"].fillna("Sin clasificar")
    joined["Producto"] = joined["Producto"].fillna("Producto no catalogado")
    joined["Categoria"] = joined["Categoria"].fillna("Sin categoría")
    joined["Tamaño"] = joined["Tamaño"].fillna("")
    joined["ProductoEtiqueta"] = joined["Producto"] + joined["Tamaño"].apply(lambda x: f" · {x}" if x else "") + " · " + joined["ProductoID"]
    joined["AñoAnalisis"] = joined["Fecha"].dt.year
    joined["MesAnalisis"] = joined["Fecha"].dt.to_period("M").dt.to_timestamp()

    metadata = {
        "registros_ventas": len(ventas),
        "clientes_catalogo": len(clientes),
        "productos_catalogo": len(productos),
        "transacciones_repetidas": int(ventas["VentaID"].duplicated().sum()),
        "sin_cliente": ids_sin_cliente,
        "sin_producto": ids_sin_producto,
        "utilidad_no_cuadra": discrepancias,
        "fecha_inicial": ventas["Fecha"].min().date(),
        "fecha_final": ventas["Fecha"].max().date(),
    }
    return joined, metadata


def kpis(df: pd.DataFrame) -> dict[str, float | int]:
    ingresos = float(df["VentaNeta"].sum())
    coste = float(df["CostoTotal"].sum())
    utilidad = ingresos - coste
    n_ventas = int(df["VentaID"].nunique())
    return {
        "ventas": ingresos,
        "costes": coste,
        "utilidad": utilidad,
        "margen": utilidad / ingresos * 100 if ingresos else 0.0,
        "ticket": ingresos / n_ventas if n_ventas else 0.0,
        "clientes": int(df["ClienteID"].nunique()),
        "transacciones": n_ventas,
        "unidades": int(df["Cantidad"].sum()),
    }


def by_dimension(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[column,"VentaNeta", "CostoTotal", "UtilidadBruta", "Cantidad", "Transacciones", "Clientes", "MargenPct", "TicketMedio"])
    output = (
        df.groupby(column, dropna=False, observed=True)
        .agg(VentaNeta=("VentaNeta", "sum"), CostoTotal=("CostoTotal", "sum"),
             UtilidadBruta=("UtilidadBruta", "sum"), Cantidad=("Cantidad", "sum"),
             Transacciones=("VentaID", "nunique"), Clientes=("ClienteID", "nunique"))
        .reset_index()
    )
    output["MargenPct"] = (output["UtilidadBruta"] / output["VentaNeta"].where(output["VentaNeta"] != 0, float("nan")) * 100).fillna(0.0)
    output["TicketMedio"] = (output["VentaNeta"] / output["Transacciones"].where(output["Transacciones"] != 0, float("nan"))).fillna(0.0)
    return output


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["MesAnalisis", "VentaNeta", "UtilidadBruta", "Transacciones"])
    return df.groupby("MesAnalisis", observed=True).agg(
        VentaNeta=("VentaNeta", "sum"), UtilidadBruta=("UtilidadBruta", "sum"),
        Transacciones=("VentaID", "nunique"),
    ).reset_index().sort_values("MesAnalisis")


def filter_data(df: pd.DataFrame, start, end, cities: list[str], stores: list[str], segments: list[str], products: list[str]) -> pd.DataFrame:
    mask = df["Fecha"].between(pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1))
    for name, selected in (("Ciudad", cities), ("Sucursal", stores), ("Segmento", segments), ("ProductoID", products)):
        if selected:
            mask &= df[name].isin(selected)
    return df.loc[mask].copy()


def commercial_insights(df: pd.DataFrame) -> list[dict[str, str]]:
    """Reglas transparentes; no sustituye al asistente de IA generativa."""
    if df.empty:
        return []
    branch = by_dimension(df,"Sucursal").sort_values("UtilidadBruta", ascending=False)
    product = by_dimension(df,"ProductoEtiqueta")
    segment = by_dimension(df,"Segmento")
    channel = by_dimension(df,"Canal") if "Canal" in df.columns else pd.DataFrame()
    insights = []
    if len(branch) >= 2:
        best, worst = branch.iloc[0], branch.iloc[-1]
        insights.append({"titulo":"Brecha entre sucursales", "evidencia":f"{best['Sucursal']} aporta ${best['UtilidadBruta']:,.0f} de utilidad bruta; {worst['Sucursal']}, ${worst['UtilidadBruta']:,.0f}.", "accion":"Comparar ventas, margen y ticket medio por tienda; identificar prácticas replicables y causas del menor rendimiento."})
    if len(product):
        leading = product.sort_values("UtilidadBruta", ascending=False).iloc[0]
        insights.append({"titulo":"Producto con mayor contribución", "evidencia":f"{leading['ProductoEtiqueta']} genera ${leading['UtilidadBruta']:,.0f} de utilidad bruta y {int(leading['Cantidad']):,} unidades.", "accion":"Revisar disponibilidad, visibilidad en carta y oportunidades de venta cruzada sin asumir que mayor venta implica mayor margen."})
        qualified = product[product["Transacciones"] >= max(5, int(len(df)*0.002))].sort_values("MargenPct")
        if not qualified.empty:
            low = qualified.iloc[0]
            insights.append({"titulo":"Margen de producto bajo vigilancia", "evidencia":f"{low['ProductoEtiqueta']} tiene margen del {low['MargenPct']:.1f}% en {int(low['Transacciones']):,} operaciones.", "accion":"Analizar mezcla de precios, costes y promociones antes de proponer ajustes; comparar productos de categorías similares."})
    if len(segment):
        leader = segment.sort_values("TicketMedio", ascending=False).iloc[0]
        insights.append({"titulo":"Segmento con mayor ticket medio", "evidencia":f"{leader['Segmento']} registra ${leader['TicketMedio']:,.2f} por transacción ({int(leader['Transacciones']):,} operaciones).", "accion":"Investigar su tamaño, recurrencia y potencial de captación antes de priorizar una campaña específica."})
    if len(channel):
        leader = channel.sort_values("VentaNeta", ascending=False).iloc[0]
        insights.append({"titulo":"Canal comercial predominante", "evidencia":f"{leader['Canal']} representa ${leader['VentaNeta']:,.0f} de ventas ({int(leader['Transacciones']):,} transacciones).", "accion":"Optimizar procesos y capacidad de este canal, pero verificar costes operativos no incluidos antes de invertir."})
    return insights


def llm_aggregates(df: pd.DataFrame) -> dict[str, Any]:
    """Enviar solo estadísticas agregadas al modelo (sin nombres ni datos personales)."""
    result: dict[str, Any] = {
        "indicadores": {k: round(v, 2) if isinstance(v, float) else v for k, v in kpis(df).items()},
        "desde": str(df["Fecha"].min().date()),
        "hasta": str(df["Fecha"].max().date()),
    }
    dimensions = {
        "sucursales": "Sucursal", "ciudades": "Ciudad", "segmentos": "Segmento",
        "productos": "ProductoEtiqueta", "canales": "Canal",
    }
    for name, column in dimensions.items():
        if column not in df:
            continue
        grouping = by_dimension(df, column).sort_values("UtilidadBruta", ascending=False)
        if name == "productos":
            grouping = grouping.head(12)
        cols = [column, "VentaNeta", "UtilidadBruta", "MargenPct", "TicketMedio", "Cantidad", "Transacciones", "Clientes"]
        result[name] = [
            {key: (round(float(val), 2) if isinstance(val, float) else int(val) if isinstance(val, int) else str(val))
             for key, val in record.items()}
            for record in grouping[cols].to_dict(orient="records")
        ]
    trend = monthly_trend(df).tail(24).copy()
    if not trend.empty:
        trend["MesAnalisis"] = trend["MesAnalisis"].dt.strftime("%Y-%m")
        result["tendencia_mensual"] = trend.round(2).to_dict(orient="records")
    return result
