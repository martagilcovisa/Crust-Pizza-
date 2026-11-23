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


def run_ai_analysis(df, question: str, api_key: str, model: str = "ggemini-3.5-flash-lite") -> str:
    """Genera análisis usando Gemini con datos comerciales agregados."""
    if not api_key:
        raise ValueError("Falta la clave de Gemini.")
    if not question.strip():
        raise ValueError("Escribe una pregunta comercial.")

    import urllib.request
    import urllib.error

    payload = llm_aggregates(df)
    body = {
        "system_instruction": {"parts": [{"text": BASE_INSTRUCTIONS}]},
        "contents": [{"role": "user", "parts": [{"text": (
            "Pregunta del director comercial:\n" + question.strip() +
            "\n\nEstadísticas calculadas del dashboard:\n" +
            json.dumps(payload, ensure_ascii=False, default=str)
        )}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1400},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"Gemini devolvió HTTP {exc.code}: {detail}") from None

    text_parts = [
        part.get("text", "")
        for candidate in result.get("candidates", [])
        for part in candidate.get("content", {}).get("parts", [])
    ]
    return "\n".join(x for x in text_parts if x).strip() or "Gemini no ha devuelto texto."
