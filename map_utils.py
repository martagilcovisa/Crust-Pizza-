"""Mapas interactivos de actividad comercial. Ciudades: puntos de referencia, no tiendas."""
from __future__ import annotations
import json
from pathlib import Path
from math import sqrt
import plotly.graph_objects as go

GEO = json.loads((Path(__file__).parent / 'map_shapes.json').read_text(encoding='utf-8'))
CITY_POINTS = {
    'Dallas': (-96.797, 32.777),
    'Houston': (-95.370, 29.760),
    'Austin': (-97.743, 30.267),
    'San Antonio': (-98.493, 29.424),
}
MAP_FIELDS = {'Ventas netas': 'VentaNeta', 'Utilidad bruta': 'UtilidadBruta',
              'Margen bruto (%)': 'MargenPct', 'Transacciones': 'Transacciones'}


def geographic_chart(city_frame, metric='Ventas netas', texas_only=False):
    """Plotly geography driven by live, filtered city metrics."""
    field = MAP_FIELDS[metric]
    features = [f for f in GEO['features'] if not texas_only or f['properties']['code'] == 'TX']
    geo = {'type':'FeatureCollection','features':features}
    states = [f['properties']['code'] for f in features]
    # A neutral state fill is used when no transactions are present; only TX has recorded sales.
    colors = [1 if state == 'TX' else 0 for state in states]
    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        geojson=geo, locations=states, featureidkey='properties.code', z=colors,
        zmin=0,zmax=1, colorscale=[[0,'#EEE7DE'],[0.499,'#EEE7DE'],[0.5,'#D4AF8C'],[1,'#D4AF8C']],
        showscale=False,marker_line_color='#D8C9BA', marker_line_width=0.75,
        hovertemplate='%{location}<extra></extra>',showlegend=False,
    ))
    data = city_frame[city_frame['Ciudad'].isin(CITY_POINTS)].copy()
    if not data.empty:
        values = data[field].clip(lower=0)
        peak = max(float(values.max()),1)
        coords = [CITY_POINTS[c] for c in data['Ciudad']]
        sizes = [(13 if texas_only else 7) + (27 if texas_only else 13)*sqrt(float(v)/peak) for v in values]
        formatted = []
        for _,r in data.iterrows():
            v = r[field]
            value = f'{v:,.2f} %' if field == 'MargenPct' else f'{int(v):,}' if field=='Transacciones' else f'{v:,.2f} USD'
            formatted.append(f"<b>{r['Ciudad']}</b><br>{metric}: {value}")
        fig.add_trace(go.Scattergeo(
            lon=[c[0] for c in coords],lat=[c[1] for c in coords],
            mode='markers+text' if texas_only else 'markers',
            text=list(data['Ciudad']) if texas_only else None,
            textposition='top center',textfont=dict(color='#493629',size=12),
            marker=dict(size=sizes,color='#945936',opacity=0.83,
                        line=dict(color='#FFF9F1',width=2)),
            hovertext=formatted,hovertemplate='%{hovertext}<extra></extra>',showlegend=False,
        ))
    fig.update_layout(
        height=365 if not texas_only else 405,
        margin=dict(l=2,r=2,t=3,b=3),
        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans,Arial',color='#493629'),
        showlegend=False,
    )
    fig.update_geos(
        visible=False,showframe=False,showcoastlines=False,
        showland=False,showcountries=False,showsubunits=False,
        bgcolor='#F9F3EB',projection_type='mercator',
        lonaxis_range=[-107.2,-92.8] if texas_only else [-125.5,-66],
        lataxis_range=[24.8,37.2] if texas_only else [24,50],
    )
    return fig
