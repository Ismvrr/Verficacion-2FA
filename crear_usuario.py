import os
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, SQLModel, Field
from passlib.context import CryptContext

# 1. Intentamos importar desde tu carpeta Models
try:
    from Models.models import Usuarios
except ImportError:
    # Si falla el import por rutas, definimos la estructura aquí mismo
    class Usuarios(SQLModel, table=True):
        id: int | None = Field(default=None, primary_key=True)
        username: str = Field(unique=True, index=True)
        password: str 
        rol: str = Field(default="usuario")
        email: str = Field(default="usuario@ejemplo.com")

# 2. Configuración de conexión y seguridad
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def crear_usuario_prueba():
    try:
        with Session(engine) as session:
            print("⏳ Encriptando contraseña...")
            h_password = pwd_context.hash("1234")
            
            nuevo = Usuarios(
                username="admin",
                password=h_password,
                email="jjesuszero05@gmail.com",
                rol="admin"
            )
            
            session.add(nuevo)
            session.commit()
            print("✅ ¡LOGRADO! Usuario 'admin' creado exitosamente.")
            
    except Exception as e:
        if "Duplicate entry" in str(e):
            print("💡 Nota: El usuario 'admin' ya existe en la base de datos.")
        else:
            print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    crear_usuario_prueba()