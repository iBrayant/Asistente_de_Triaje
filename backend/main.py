from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agente import ErrorAgente, triar

app = FastAPI(title="Asistente de Triaje")

# Solo local: el front se abre como archivo o desde un servidor estático local.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Turno(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class Entrada(BaseModel):
    mensaje: str = Field(min_length=1, max_length=2000)
    historial: list[Turno] = Field(default_factory=list, max_length=20)


@app.post("/triaje")
def triaje(entrada: Entrada):
    try:
        return triar(entrada.mensaje.strip(), [t.model_dump() for t in entrada.historial])
    except ErrorAgente as e:
        raise HTTPException(status_code=502, detail=str(e))


# Sirve el frontend en http://localhost:8000/ (después de las rutas de la API)
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
