import os
import secrets
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, SQLModel
from passlib.context import CryptContext

from Models.models import Usuarios, Tokens

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def crear_usuario_prueba():
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            h_password = pwd_context.hash("1234")
            nuevo = Usuarios(
                username="admin",
                password=h_password,
                email="ismaelrmzhdz@gmail.com",
                rol="admin",
                two_factor_enabled=True,
                two_factor_length=6,
                two_factor_type=1,
                two_factor_method=2
            )
            session.add(nuevo)
            session.commit()
            session.refresh(nuevo)

            token = secrets.token_hex(25)
            nuevo_token = Tokens(token=token, activo=True, usuario_id=nuevo.id, creado_por_id=nuevo.id)
            session.add(nuevo_token)
            session.commit()

            print(f"Usuario 'admin' creado exitosamente.")
            print(f"Token de acceso: {token}")
    except Exception as e:
        if "Duplicate entry" in str(e) or "UNIQUE constraint" in str(e):
            print("El usuario 'admin' ya existe.")
        else:
            print(f"Error inesperado: {e}")

if __name__ == "__main__":
    crear_usuario_prueba()
