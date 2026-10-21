# Asistente de Triaje

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Llama%203%208B-000000)
![Licencia](https://img.shields.io/badge/licencia-MIT-green)

Asistente de triaje médico que corre **100 % en local**. El paciente describe sus síntomas en lenguaje natural y el sistema responde con la **especialidad médica sugerida**, el **nivel de urgencia** y una justificación corta. Si la información no alcanza, **pregunta en vez de inventar**.

> Proyecto del Taller Práctico de Inteligencia Artificial (803 M), Universidad de Cundinamarca.

<!-- TODO: reemplazar por una captura o GIF del chat (guardar en docs/img/) -->
<!-- ![Demo](docs/img/demo.gif) -->

## Características

- **Privacidad:** Llama 3 8B corre en tu equipo vía Ollama; ningún dato de salud sale de la máquina.
- **Salida estructurada:** el modelo responde JSON, que el backend valida (campos, urgencia, acción) antes de entregarlo.
- **Agente con dos acciones:** sugerir una especialidad o pedir más información.
- **Seguro por diseño:** nunca receta ni da diagnósticos cerrados; solo orienta.
- **Robusto:** reintenta una vez si el JSON es inválido o truncado, y responde `502` con un mensaje claro si falla.
- **Memoria de conversación sin estado en el servidor:** el historial vive solo en el navegador.

## Stack

Python · FastAPI · Pydantic · Ollama (Llama 3 8B) · HTML/JS

## Arquitectura

```
Navegador (index.html) → FastAPI (main.py) → agente.py → Ollama (Llama 3 8B)
        ↑                                                       │
        └────────────── JSON validado ←────────────────────────┘
```

```
backend/   main.py (API /triaje) · agente.py (prompt + Ollama + validación) · requirements.txt
frontend/  index.html (chat, sin build)
docs/      RESUMEN.md (documentación detallada del proyecto)
```

## Cómo correrlo

**1. Ollama**

```bash
ollama pull llama3
ollama serve        # si no está corriendo ya (puerto 11434)
```

**2. Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**3. Frontend**

Con el backend corriendo, abre http://localhost:8000/ (el backend sirve el frontend).
Documentación interactiva de la API: http://localhost:8000/docs

## API

`POST /triaje` con `{"mensaje": "texto del paciente", "historial": [...]}`.

`historial` es opcional: los turnos anteriores (`{"role": "user" | "assistant", "content": "..."}`) para que el agente recuerde la consulta. El servidor no guarda nada y el botón "Nueva consulta" lo borra.

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

Si falta información:

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

## Ejemplos de prueba

```bash
curl -s localhost:8000/triaje -H 'Content-Type: application/json' -d '{"mensaje":"..."}'
```

| Caso | Mensaje | Esperado |
|---|---|---|
| Síntomas claros | "Desde ayer tengo dolor fuerte en el pecho que se va al brazo izquierdo, sudo frío y me falta el aire." | `sugerir_especialidad`, Cardiología, urgencia alta |
| Caso ambiguo | "Me duele la barriga y me siento mareado desde hace dos días, además tengo la piel un poco amarilla." | `sugerir_especialidad` (p. ej. Gastroenterología / Medicina interna), justificación prudente, sin diagnóstico cerrado |
| Información incompleta | "Me siento mal." | `solicitar_informacion` con una pregunta, `especialidad_sugerida: null` |
| Petición de medicamento | "¿Qué pastilla me tomo para la gripa?" | No debe recetar |

Llama 3 no es determinista al 100 %: los resultados exactos pueden variar levemente; lo importante es el comportamiento esperado.

## Decisiones de diseño

- **Hiperparámetros:** `temperature=0.1`, `top_p=0.9`, `num_predict=150` (equivalente a `max_tokens` en Ollama).
- **`format="json"`** obliga al modelo a emitir JSON válido.
- **Few-shot:** dos ejemplos de conversación anclan el formato y el comportamiento.
- **Fecha:** la calcula Python (`datetime.date`), se inserta en el system prompt y el backend sobrescribe el campo `fecha` de la respuesta.
- **Normalización:** `accion` y `nivel_urgencia` se normalizan (tildes, mayúsculas) porque el modelo a veces varía la escritura.

Más detalle (system prompt, flujo de una consulta, logs, limitaciones) en [docs/RESUMEN.md](docs/RESUMEN.md).

## Aviso

Proyecto académico y demostrativo. **No es un dispositivo médico** y no reemplaza la valoración de un profesional de la salud. Ante una emergencia, acude a urgencias o llama a la línea 123.

## Autor

**Brayant Vásquez Gómez** · [GitHub](https://github.com/iBrayant) · [LinkedIn](https://linkedin.com/in/brayant-vásquez-gómez)

Licencia [MIT](LICENSE).
