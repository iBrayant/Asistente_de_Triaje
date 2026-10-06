# Asistente de Triaje

Taller Práctico — Inteligencia Artificial (803 M), Universidad de Cundinamarca.

Backend FastAPI que recibe los síntomas de un paciente, los envía a **Llama 3 8B** (vía Ollama, 100 % local) y devuelve un JSON con la especialidad médica sugerida. Ningún dato sale de la máquina.

## Estructura

```
backend/   main.py (API /triaje) · agente.py (prompt + Ollama + validación) · requirements.txt
frontend/  index.html (página de prueba)
```

## Cómo correrlo

### 1. Ollama
```bash
ollama pull llama3
ollama serve        # si no está corriendo ya (puerto 11434)
```

### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Documentación interactiva: http://localhost:8000/docs

### 3. Frontend
Con el backend corriendo, abre http://localhost:8000/ (el backend sirve el frontend).

## API

`POST /triaje` con `{"mensaje": "texto del paciente", "historial": [...]}`.

`historial` es opcional: la lista de turnos anteriores (`{"role": "user" | "assistant", "content": "..."}`) para que el agente recuerde la consulta. El servidor no guarda nada; el historial vive solo en el navegador y se borra con "Nueva consulta".

Respuesta con información suficiente:
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
Si falta información, el agente pregunta en vez de inventar:
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

## Decisiones de diseño

- Hiperparámetros: `temperature=0.1`, `top_p=0.9`, `num_predict=150` (equivalente a `max_tokens` en Ollama).
- `format="json"` obliga al modelo a emitir JSON válido.
- La fecha la calcula Python (`datetime.date`) y se inserta en el system prompt; además el backend sobrescribe el campo `fecha` de la respuesta.
- Si el JSON es inválido o está truncado por el límite de 150 tokens, se reintenta una vez; si vuelve a fallar, la API responde `502` con un mensaje claro (también si Ollama no está disponible).
- El agente nunca receta ni diagnostica: solo sugiere especialidad.

## Ejemplos de prueba

```bash
curl -s localhost:8000/triaje -H 'Content-Type: application/json' -d '{"mensaje":"..."}'
```

> Llama 3 no es determinista al 100 %: los resultados exactos pueden variar levemente. Lo importante es el comportamiento esperado.

**1. Síntomas claros**
`"Desde ayer tengo dolor fuerte en el pecho que se va al brazo izquierdo, sudo frío y me falta el aire."`
Esperado: `sugerir_especialidad`, Cardiología, urgencia `alta`.

**2. Caso ambiguo**
`"Me duele la barriga y me siento mareado desde hace dos días, además tengo la piel un poco amarilla."`
Esperado: `sugerir_especialidad` (p. ej. Gastroenterología / Medicina interna) con justificación prudente, urgencia `media` o `alta`, sin diagnóstico cerrado.

**3. Información incompleta**
`"Me siento mal."`
Esperado: `solicitar_informacion` con una pregunta sobre qué síntomas tiene, `especialidad_sugerida: null`.

Cualquier prueba adicional: pedir un medicamento (`"¿Qué pastilla me tomo para la gripa?"`) debe seguir sin recetar.
