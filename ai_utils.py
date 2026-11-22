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


def run_ai_analysis(df, question: str, api_key: str, model: str = "gpt-4.1-mini") -> str:
    if not api_key:
        raise ValueError("Falta la clave API de la IA.")
    if not question.strip():
        raise ValueError("Escribe una pregunta comercial.")
    from openai import OpenAI
    client = OpenAI(api_key=api_key, timeout=45)
    payload = llm_aggregates(df)
    reply = client.chat.completions.create(
        model=model,
        messages=[
            {"role":"system", "content":BASE_INSTRUCTIONS},
            {"role":"user", "content": "Pregunta del director comercial:\n" + question.strip() + "\n\nEstadísticas calculadas a partir del dashboard:\n" + json.dumps(payload, ensure_ascii=False, default=str)},
        ],
        temperature=0.2,
        max_tokens=1000,
    )
    return reply.choices[0].message.content or "El modelo no ha devuelto texto."
