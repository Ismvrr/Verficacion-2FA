from fastapi import FastAPI
from Config.db import engine
from sqlmodel import SQLModel
import Models
from Routers import auth, telefono, admin
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI(title = "2FA + Verificacion de Telefonos")

@app.on_event("startup")
def Inicio():
    SQLModel.metadata.create_all(engine)

app.add_middleware( CORSMiddleware, allow_origins=["*"], allow_credentials = True, allow_methods = ["*"], allow_headers = ["*",])

app.include_router(auth.router)
app.include_router(telefono.router)
app.include_router(admin.router)

@app.get("/", tags = ["Frontend"])
async def paginaWeb():
    return FileResponse("frontend/dashboard.html")

@app.get("/telefonos", tags = ["Frontend"])
async def paginaTelefonos():
    return FileResponse("frontend/telefonos.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


