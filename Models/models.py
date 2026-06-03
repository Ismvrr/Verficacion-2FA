from sqlmodel import SQLModel, Field
from pydantic import BaseModel
from sqlalchemy import Column, BigInteger
from datetime import datetime, timedelta

class Telefonos(SQLModel, table  = True):
      id: int | None = Field(default = None, index= True, primary_key = True)
      numero: str = Field(max_length = 12)
      tipo: str
      compañia: str
      codigo_pais: str
      pais: str
      api_Utilizada: str
      
class Tokens (SQLModel, table = True):
      id : int | None = Field(default = None, primary_key = True)
      token : str = Field (unique = True, index = True)
      activo: bool = Field(default = True)
      usuario_id: int | None = Field (default = None, foreign_key = "usuarios.id")
      creado_por_id: int | None = Field(default = None, foreign_key="usuarios.id")

class ProveedoresAPI(SQLModel, table = True):
      id: int | None = Field(default = None, primary_key = True)
      nombre: str = Field(unique = True, index = True)
      url_base: str
      api_key: str
      activa : bool = Field(default = True)
#peticiones
      parametro_num : str
      parametro_key : str
#mapeo
      llave_validacion : str
      llave_numero: str
      llave_pais: str
      llave_tipo: str
      valor_celular: str
      llave_codigo: str
      llave_company :str

#Tabla para el csv local.
class Numeraciones(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    zona: str
    numeracion_inicial: int = Field(sa_column=Column(BigInteger, index=True)) 
    numeracion_final: int = Field(sa_column=Column(BigInteger, index=True))
    ocupacion: str | None
    modalidad: str
    proveedor: str
    fecha_asignacion: str | None

#Recibe las busquedas
class Solicitud(BaseModel):
#se define un field para establecer el minimo y maximo de caracteres
    telefono: str = Field(min_length=12, max_length=15)

class Usuarios(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password: str 
    rol: str = Field(default="usuario")
    email: str = Field(default="usuario@ejemplo.com") 
    otp_length: int = Field(default=6)
    otp_type: str = Field(default="numeric") 

class TwoFactorCodes(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuarios.id", index=True)
    hashed_code: str
    is_used: bool = Field(default=False)
    attempts: int = Field(default=0)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=5))