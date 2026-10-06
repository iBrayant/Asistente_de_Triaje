# Resumen del proyecto: Asistente de Triaje

Taller Práctico — Inteligencia Artificial (803 M), Universidad de Cundinamarca.

## 1. ¿Qué es?

Un asistente de triaje médico. El paciente escribe sus síntomas en lenguaje normal y el sistema responde con:

- la **especialidad médica** que le conviene consultar,
- el **nivel de urgencia** (baja, media o alta),
- una **justificación** corta.

No receta medicamentos ni da diagnósticos cerrados: solo orienta, como un enfermero de triaje. Si el mensaje no trae síntomas claros (por ejemplo, "estoy embarazada"), el asistente **pregunta** en vez de inventar.

Todo corre **en el computador local**. No se usa ninguna API en la nube, porque son datos de salud.

## 2. Arquitectura

```
Navegador (index.html) → FastAPI (main.py) → agente.py → Ollama (Llama 3 8B)
        ↑                                                       │
        └────────────── JSON validado ←────────────────────────┘
```

| Capa | Archivo | Qué hace |
|---|---|---|
| Frontend | `frontend/index.html` | Chat en HTML/JS simple, sin build. Muestra preguntas del agente y la tarjeta de resultado. |
| API | `backend/main.py` | FastAPI con `POST /triaje`. También sirve el frontend en `http://localhost:8000/`. |
| Agente | `backend/agente.py` | System prompt, llamada al modelo, validación del JSON, reintento y logs. |
| Modelo | Ollama | Sirve Llama 3 8B de forma local. |

## 3. Modelo de IA y configuración

- **Modelo:** Llama 3 (8B), modelo libre de Meta, servido localmente con **Ollama** (`ollama pull llama3`).
- **Librería de integración:** `ollama-python`.

**Hiperparámetros**

| Parámetro | Valor | Para qué |
|---|---|---|
| `temperature` | 0.1 | Respuestas estables y poco creativas, importante en salud. |
| `top_p` | 0.9 | Limita el muestreo a las palabras más probables. |
| `num_predict` (max_tokens) | 150 | Respuestas cortas. Si el JSON se trunca, se reintenta. |
| `format` | `"json"` | Obliga al modelo a emitir JSON válido. |

## 4. Reglas del agente (system prompt)

- Actúa como enfermero experto en triaje y habla en español sencillo.
- Nunca receta medicamentos ni da diagnósticos cerrados; solo sugiere especialidad.
- No inventa síntomas ni especialidades sin fundamento.
- Si falta información clave, pregunta antes de sugerir.
- Responde siempre y solo con el JSON definido.
- La **fecha la calcula Python** (`datetime.date`) y se inserta en el prompt. Además, el backend sobrescribe el campo `fecha` de la respuesta.
- Se incluyen **dos ejemplos de conversación** (few-shot) para anclar el formato y el comportamiento.

## 5. Formato de respuesta

Con información suficiente:

```json
{
  "accion": "sugerir_especialidad",
  "sintomas_reportados": ["..."],
  "especialidad_sugerida": "...",
  "nivel_urgencia": "baja | media | alta",
  "justificacion": "...",
  "fecha": "YYYY-MM-DD"
}
```

Si falta información (segunda acción, añadida para poder preguntar):

```json
{
  "accion": "solicitar_informacion",
  "sintomas_reportados": [],
  "especialidad_sugerida": null,
  "nivel_urgencia": null,
  "pregunta": "...",
  "fecha": "YYYY-MM-DD"
}
```

## 6. Cómo funciona una consulta

1. El paciente escribe en el chat y pulsa "Enviar".
2. El navegador manda `POST /triaje` con `{"mensaje": "...", "historial": [...]}`.
3. `agente.py` arma los mensajes: system prompt con la fecha, ejemplos, historial y el mensaje nuevo.
4. Llama 3 responde en JSON.
5. Se valida: JSON correcto, campos obligatorios, urgencia válida y acción conocida.
6. Si es inválido o está truncado, **reintenta una vez**. Si vuelve a fallar, la API responde `502` con un mensaje claro (también si Ollama no está disponible).
7. El frontend muestra la pregunta o la tarjeta de resultado.

**Memoria de la conversación:** el historial vive solo en el navegador y se envía en cada petición. El servidor no guarda nada. El botón "Nueva consulta" lo borra.

## 7. Logs

En la terminal de uvicorn el agente imprime la consulta, la **respuesta cruda del modelo**, el tiempo de cada intento y los errores de validación. Los logs de Ollama se ven con `sudo snap logs ollama -f`. `ollama ps` muestra el modelo cargado y si usa CPU o GPU.

## 8. Cómo correrlo

```bash
ollama pull llama3
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Luego abre http://localhost:8000/. La documentación de la API está en http://localhost:8000/docs.

## 9. Limitaciones

- Llama 3 8B no es determinista al 100 %: las respuestas pueden variar un poco.
- El límite de 150 tokens puede truncar el JSON; por eso existe el reintento.
- No es un dispositivo médico: no reemplaza la valoración de un profesional.
- La primera consulta tras un rato sin uso tarda más, porque Ollama vuelve a cargar el modelo.
- El historial largo ocupa parte del contexto del modelo (4096 tokens).

## 10. Conceptos de IA que demuestra

- Ingeniería de prompts: system prompt, reglas y few-shot.
- Hiperparámetros de generación: temperatura, top_p y límite de tokens.
- Ejecución local de un modelo libre (LLM) con Ollama.
- Salida estructurada, validación y reintento.
- Agente con dos acciones: sugerir especialidad o pedir más información.
- Privacidad: ningún dato de salud sale del equipo.
