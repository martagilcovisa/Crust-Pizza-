# San Francisco Crust Pizza · Dashboard Business Intelligence

Proyecto académico de la asignatura Sistemas de Información para la Toma de Decisiones Comerciales. Realizado en **Python + Streamlit**, con tema crema/café, visualizaciones interactivas, mapas de Texas y EE. UU., carga de Excel y asistente generativo opcional.

## Publicación en Streamlit Community Cloud

1. Descomprime el ZIP. Dentro encontrarás `app.py`, `requirements.txt`, `data/`, etc.
2. Abre https://github.com/new (necesitas una cuenta GitHub). Crea un repositorio, por ejemplo `crust-pizza-dashboard`, y pulsa **Create repository**.
3. En el nuevo repositorio, ve a **Add file → Upload files**. Arrastra **el contenido descomprimido** de la carpeta `Crust_Pizza_Para_Publicar`, conservando las carpetas `data/` y `.streamlit/`. No subas solo el ZIP: GitHub debe poder ver el archivo `app.py`. Confirma **Commit changes**.
4. Abre https://share.streamlit.io/ y entra con GitHub. Pulsa **Create app → Yup, I have an app** y selecciona repositorio, rama `main` y archivo `app.py`. Pulsa **Deploy**. Espera a ver el dashboard; copia su URL pública `https://...streamlit.app/`.
5. Abre el enlace en una ventana de incógnito y comprueba KPIs, filtros, mapas y carga de Excel. Pega el enlace en el documento del máster.

## IA generativa — activación opcional

La pestaña *Asistente IA* genera hallazgos sin conexión. Para activar el botón **Generar recomendaciones con IA**, crea una clave API en https://platform.openai.com/api-keys/ (servicio separado de ChatGPT, sujeto a facturación). En **Streamlit → App settings → Secrets**, añade en formato TOML:

```toml
OPENAI_API_KEY = "tu_clave_aqui"
```

No publiques una clave en GitHub, en el ZIP ni en mensajes de chat. Configura un límite de gasto en la plataforma API; toda persona que pueda visitar la web pública podrá utilizar el asistente conectado y consumir saldo.

## Protección de datos

El Excel de clientes incluido en esta versión pública contiene **solo `ClienteID` y `Segmento`**. Se eliminaron los nombres, edades y demás datos no necesarios para el dashboard. Conserva los Excel completos originales por separado si necesitas compararlos. Los importes y resultados del dashboard permanecen iguales. Para una publicación pública confirma con la universidad que los datos comerciales simulados del caso se pueden compartir.

## Sobre los mapas

Los datos comerciales se concentran en las cuatro ciudades de Texas. El mapa muestra puntos aproximados de ciudad y permite visualizar las cifras con hover. **En Streamlit, cambia la ciudad mediante los botones Dallas/Houston/Austin/San Antonio o el filtro lateral**, en lugar de hacer clic sobre el círculo del mapa. Se conserva la ciudad seleccionada y puedes pasar a otra sin bloquearte. Cualquier ciudad fuera de las cuatro conocidas sigue computando en KPIs y tablas; para ubicarla en el mapa es necesario añadir coordenadas.

## Actualización de bases de datos

En la barra lateral se incluyen tres campos para subir Excel: ventas, clientes y productos. El panel recalcula indicadores, gráficos y mapas con los nuevos datos. Los cambios son temporales durante la sesión (no sobrescriben los archivos del repositorio). Si cambia el periodo o catálogo, los filtros se restablecen para evitar valores antiguos.

## Requisitos de columnas

- Ventas: `VentaID`, `Fecha`, `Ciudad`, `Sucursal`, `ClienteID`, `ProductoID`, `Cantidad`, `VentaNeta`, `CostoTotal`.
- Clientes: `ClienteID`, `Segmento`.
- Productos: `ProductoID`, `Producto`.

## Comprobación local

Requiere Python 3.12 recomendado. Desde esta carpeta:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

La primera carga puede tardar algo más al procesar las 45.900 operaciones. El proyecto no necesita conectarse a ninguna cuenta comercial para visualizar el dashboard; solo la IA generativa requiere su clave API.

## Metodología de los indicadores

Se usan los importes históricos `VentaNeta` y `CostoTotal` de cada venta. `UtilidadBruta = VentaNeta - CostoTotal`; `MargenBruto = UtilidadBruta/VentaNeta`; `TicketPromedio = VentaNeta / numero de VentaID distintos`. `ClienteID` y `ProductoID` enlazan las tres tablas. Las recomendaciones de IA deben analizarse críticamente y no sustituyen las decisiones humanas.
