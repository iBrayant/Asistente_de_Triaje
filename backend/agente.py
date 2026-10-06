"""Agente de triaje: arma el system prompt, llama a Ollama y valida el JSON."""
import json
import logging
import time
from datetime import date

import ollama

logging.basicConfig(level=logging.INFO, format="%(asctime)s [agente] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("agente")

MODELO = "llama3"
OPCIONES = {"temperature": 0.1, "top_p": 0.9, "num_predict": 150}  # num_predict = max_tokens
URGENCIAS = {"baja", "media", "alta"}

SYSTEM_PROMPT = """Actúas como un enfermero experto en triaje. Hablas en español sencillo.

Reglas:
- NUNCA recetes medicamentos ni des diagnósticos cerrados. Solo sugieres la especialidad médica.
- No inventes síntomas ni especialidades sin fundamento. Usa solo lo que el paciente dijo.
- Si falta información clave (qué siente, dónde, desde cuándo, intensidad), pregunta ANTES de sugerir.
- Si el mensaje no describe síntomas, pide información.
- Responde SIEMPRE y SOLO con un objeto JSON, sin texto fuera del JSON.
- Habla SOLO de lo que el paciente escribió. No supongas datos (embarazo, edad, enfermedades) que el paciente no mencionó; si los mencionó, tenlos en cuenta.
- Usa "solicitar_informacion" únicamente si el mensaje no describe ningún síntoma concreto; si hay al menos un síntoma claro, sugiere una especialidad.
- Mantén "justificacion" y "pregunta" en una sola frase corta.

Fecha de hoy: {fecha}. Usa exactamente esta fecha en el campo "fecha".

Cuando tengas información suficiente responde con:
{{
  "accion": "sugerir_especialidad",
  "sintomas_reportados": ["..."],
  "especialidad_sugerida": "...",
  "nivel_urgencia": "baja | media | alta",
  "justificacion": "...",
  "fecha": "{fecha}"
}}

Cuando falte información clave responde con:
{{
  "accion": "solicitar_informacion",
  "sintomas_reportados": ["..."],
  "especialidad_sugerida": null,
  "nivel_urgencia": null,
  "pregunta": "...",
  "fecha": "{fecha}"
}}
"""

CAMPOS_COMUNES = {"accion", "sintomas_reportados", "especialidad_sugerida", "nivel_urgencia", "fecha"}


class ErrorAgente(Exception):
    """El modelo no respondió o devolvió algo inválido tras reintentar."""


def ejemplos(fecha: str) -> list[dict]:
    """Conversaciones de ejemplo (few-shot) para anclar el formato y el comportamiento."""
    def r(d):
        return json.dumps({**d, "fecha": fecha}, ensure_ascii=False)
    return [
        {"role": "user", "content": "Me duele mucho la garganta y tengo fiebre desde hace dos días."},
        {"role": "assistant", "content": r({
            "accion": "sugerir_especialidad", "sintomas_reportados": ["dolor de garganta", "fiebre"],
            "especialidad_sugerida": "Otorrinolaringología", "nivel_urgencia": "media",
            "justificacion": "El dolor de garganta con fiebre se evalúa en otorrinolaringología."})},
        {"role": "user", "content": "Me siento mal."},
        {"role": "assistant", "content": r({
            "accion": "solicitar_informacion", "sintomas_reportados": [],
            "especialidad_sugerida": None, "nivel_urgencia": None,
            "pregunta": "¿Qué molestia tienes, en qué parte del cuerpo y desde cuándo?"})},
    ]


def construir_system_prompt() -> str:
    # La fecha la calcula Python, nunca el modelo.
    return SYSTEM_PROMPT.format(fecha=date.today().isoformat())


def validar(data: dict, fecha: str) -> dict:
    if not isinstance(data, dict):
        raise ValueError("la respuesta no es un objeto JSON")
    faltan = CAMPOS_COMUNES - data.keys()
    if faltan:
        raise ValueError(f"faltan campos: {sorted(faltan)}")
    if not isinstance(data["sintomas_reportados"], list):
        raise ValueError("sintomas_reportados debe ser una lista")

    if data["accion"] == "sugerir_especialidad":
        if not data.get("justificacion"):
            raise ValueError("falta justificacion")
        if not data["especialidad_sugerida"]:
            raise ValueError("falta especialidad_sugerida")
        if data["nivel_urgencia"] not in URGENCIAS:
            raise ValueError("nivel_urgencia debe ser baja, media o alta")
    elif data["accion"] == "solicitar_informacion":
        if not data.get("pregunta"):
            raise ValueError("falta pregunta")
    else:
        raise ValueError(f"accion desconocida: {data['accion']!r}")

    data["fecha"] = fecha  # se fuerza la fecha calculada por el backend
    return data


def triar(mensaje: str, historial: list[dict] | None = None, cliente: ollama.Client | None = None) -> dict:
    cliente = cliente or ollama.Client()
    fecha = date.today().isoformat()
    mensajes = [
        {"role": "system", "content": construir_system_prompt()},
        *ejemplos(fecha),
        *(historial or []),  # turnos previos de esta consulta (los guarda el navegador)
        {"role": "user", "content": mensaje},
    ]
    ultimo_error = "desconocido"
    log.info("Consulta: %r (turnos previos: %d)", mensaje, len(historial or []))
    for intento in (1, 2):  # intento inicial + 1 reintento
        inicio = time.perf_counter()
        try:
            resp = cliente.chat(model=MODELO, messages=mensajes, options=OPCIONES, format="json")
        except Exception as e:  # Ollama caído, modelo no descargado, etc.
            log.error("Ollama no respondió: %s", e)
            raise ErrorAgente(f"No se pudo contactar a Ollama: {e}") from e
        crudo = resp["message"]["content"]
        log.info("Intento %d (%.1fs) respuesta cruda: %s", intento, time.perf_counter() - inicio, crudo)
        try:
            resultado = validar(json.loads(crudo), fecha)
            log.info("Válida -> accion=%s", resultado["accion"])
            return resultado
        except (json.JSONDecodeError, ValueError) as e:
            ultimo_error = str(e)
            log.warning("Intento %d inválido: %s", intento, e)
    raise ErrorAgente(f"El modelo devolvió una respuesta inválida tras reintentar: {ultimo_error}")
