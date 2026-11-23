"""Conexión opcional con un modelo de IA generativa; usa solo datos agregados."""
import json

from data_utils import llm_aggregates

BASE_INSTRUCTIONS = """Eres el asistente de inteligencia comercial de San Francisco Crust Pizza.
Responde EN ESPAÑOL, con estilo claro, ejecutivo y útil para un director comercial.
Usa EXCLUSIVAMENTE los datos agregados proporcionados en el mensaje del usuario.
No inventes datos, tasas de crecimiento, comparativas con la industria ni causas no demostradas.
Distingue los hechos observados de las hipótesis por verificar.
Sustenta cada recomendación en cifras del dashboard, explicita las limitaciones
(margen bruto no equivale a beneficio neto; no se incluyen gastos fijos ni marketing),
y sugiere una acción concreta verificable. El margen bruto es utilidad bruta / ventas netas.
Si falta evidencia para responder, indícalo. No uses nombres de personas ni datos sensibles.
Devuelve un máximo de seis párrafos o puntos, salvo petición expresa de mayor detalle.
"""


# Modelos candidatos mostrados con cuota gratuita en el proyecto del usuario.
# Se verifican contra models.list para esta clave antes de utilizarlos.
CANDIDATE_MODELS = (
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-3-flash",
)


def _http_json(url, api_key, body=None, timeout=30):
    """Comunicación REST con Google; nunca incluye la clave en la URL."""
    import urllib.request
    import urllib.error
    headers = {"x-goog-api-key": api_key, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url,
        headers=headers,
        data=(json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None),
        method=("POST" if body is not None else "GET"),
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def _available_models(api_key):
    """Lista únicamente modelos habilitados para generateContent en esta clave."""
    import urllib.parse
    base = "https://generativelanguage.googleapis.com/v1beta/models"
    found = []
    token = ""
    for _ in range(8):  # límite preventivo de paginación
        url = base + ("?" + urllib.parse.urlencode({"pageToken": token, "pageSize": 100}) if token else "?pageSize=100")
        result = _http_json(url, api_key, timeout=20)
        for item in result.get("models", []):
            if "generateContent" in item.get("supportedGenerationMethods", []):
                found.append(item.get("name", "").removeprefix("models/"))
        token = result.get("nextPageToken", "")
        if not token:
            break
    return list(dict.fromkeys(found))


def _format_error(exc):
    import urllib.error
    if isinstance(exc, urllib.error.HTTPError):
        # No revelar URL, datos enviados, ni la clave.
        return exc.code
    return None


def run_ai_analysis(df, question: str, api_key: str, model: str = "gemini-3.1-flash-lite") -> str:
    """Responde con Gemini, con selección verificada y tolerancia a sobrecargas.

    Solo usa candidatos con cuota gratuita indicada por el usuario. No conmuta
    automáticamente a modelos de pago. No garantiza disponibilidad del proveedor.
    """
    import time
    import urllib.error

    if not api_key:
        raise ValueError("Falta la clave API de Gemini en Secrets de Streamlit.")
    if not question or not question.strip():
        raise ValueError("Escribe una pregunta comercial.")

    payload = llm_aggregates(df)
    body = {
        "system_instruction": {"parts": [{"text": BASE_INSTRUCTIONS}]},
        "contents": [{"role": "user", "parts": [{"text": (
            "Pregunta del director comercial:\n" + question.strip()
            + "\n\nEstadísticas calculadas del dashboard:\n"
            + json.dumps(payload, ensure_ascii=False, default=str)
        )}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1400},
    }

    try:
        available = _available_models(api_key)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError("La clave de Gemini no tiene acceso. Revisa Secrets y el proyecto de Google AI Studio.") from None
        if exc.code == 429:
            raise RuntimeError("El proyecto ha alcanzado su cuota de Gemini. Prueba más tarde.") from None
        raise RuntimeError(f"No se pudo consultar la lista de modelos de Gemini (HTTP {exc.code}).") from None
    except (OSError, ValueError) as exc:
        raise RuntimeError("No se pudo consultar la lista de modelos por un problema de conexión.") from None

    preferred = [model] + [m for m in CANDIDATE_MODELS if m != model]
    candidates = [m for m in preferred if m in available and m in CANDIDATE_MODELS]
    if not candidates:
        raise RuntimeError(
            "La clave funciona, pero ninguno de los modelos gratuitos configurados aparece habilitado "
            "para generateContent. Revisa AI Studio > Límites de frecuencia."
        )

    overloaded = False
    for model_id in candidates:
        for attempt in range(2):
            try:
                result = _http_json(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent",
                    api_key, body=body, timeout=45,
                )
                texts = [
                    part.get("text", "")
                    for candidate in result.get("candidates", [])
                    for part in candidate.get("content", {}).get("parts", [])
                ]
                response = "\n".join(t for t in texts if t).strip()
                if response:
                    return response
                raise RuntimeError("Gemini respondió, pero no devolvió texto. Intenta otra pregunta.")
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403):
                    raise RuntimeError("Gemini ha rechazado la clave o el permiso del proyecto.") from None
                if exc.code == 429:
                    # Un límite global no se resuelve probando todos los modelos.
                    raise RuntimeError("Gemini ha alcanzado el límite gratuito de solicitudes. Prueba más tarde.") from None
                if exc.code in (404, 400):
                    # Algunos modelos pueden estar listados y no servir para generateContent.
                    break
                if exc.code in (500, 502, 503, 504):
                    overloaded = True
                    if attempt == 0:
                        time.sleep(2)
                        continue
                    break
                raise RuntimeError(f"Gemini rechazó la solicitud (HTTP {exc.code}).") from None
            except (TimeoutError, OSError):
                overloaded = True
                if attempt == 0:
                    time.sleep(2)
                    continue
                break
    if overloaded:
        raise RuntimeError(
            "Los modelos gratuitos disponibles están temporalmente saturados (503). "
            "El dashboard sigue funcionando; prueba más tarde."
        )
    raise RuntimeError("Los modelos disponibles no admitieron la petición. Consulta los permisos en Google AI Studio.")
