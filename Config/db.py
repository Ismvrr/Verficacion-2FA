# db.py
import os
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, Session as SessionType
from typing import Annotated, Generator
from fastapi import Depends

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") 
if not DATABASE_URL:
    raise ValueError("No se encontró DATABASE_URL en el archivo .env")

engine = create_engine(DATABASE_URL, echo=True)

def get_Session() -> Generator[SessionType, None, None]: 
    with Session(engine) as session:
          yield session

SessionDep = Annotated[SessionType, Depends(get_Session)]