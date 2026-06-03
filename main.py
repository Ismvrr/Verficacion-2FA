from fastapi import FastAPI
from Config.db import engine
from sqlmodel import SQLModel
import Models
from Routers import telefono, auth
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI(title = "Validación de teléfonos")

@app.on_event("startup")
def Inicio():
    SQLModel.metadata.create_all(engine)

app.add_middleware( CORSMiddleware, allow_origins=["*"], allow_credentials = True, allow_methods = ["*"], allow_headers = ["*",])

app.include_router(auth.router)

@app.get("/", tags = ["Frontend"])
async def paginaWeb():
    return FileResponse("frontend/index.html")
