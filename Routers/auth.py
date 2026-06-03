import secrets
import csv
import io
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.security import APIKeyHeader
from sqlmodel import Session, select
from Config.db import get_Session
from Models.models import Usuarios, Tokens, ProveedoresAPI, Numeraciones, Usuarios, TwoFactorCodes
from Utils import securityUtil
from Services import recaptchaService, authService


router = APIRouter(prefix = "/auth", tags = ["Login"])

@router.post("/login")
#Login
async def login(username:str, password: str, session: Session = Depends(get_Session)):
    statement = select(Usuarios).where(Usuarios.username == username)
    user_db = session.exec(statement).first()

    if not user_db or user_db.password != password:
        raise HTTPException(status_code = 401, detail = "Usuario o contraseña incorrecta.")

    statementToken = select(Tokens).where(Tokens.usuario_id == user_db.id, Tokens.activo == True)
    token_db = session.exec(statementToken).first()

    if not token_db:
       raise HTTPException(status_code = 403, detail = "login correctom pero no tienes asignado un token.")

    return {"mensaje": "login correcto", "token": token_db.token}

# Validar el token

header_scheme = APIKeyHeader(name = "Authorization")

async def validarToken(token:str = Depends(header_scheme), session: Session = Depends(get_Session)):
    statement = select(Tokens).where(Tokens.token == token)
    token_db = session.exec(statement).first()

    if not token_db:
        raise HTTPException(status_code=403, detail="Token inválido o no existe.")
    if not token_db.activo:
        raise HTTPException(status_code=403, detail="Este token está dado de baja.")
    if not token_db.usuario_id:
        raise HTTPException(status_code=403, detail="El token es válido pero no está asignado a ningún usuario.")

    statementUsuario = select(Usuarios).where(Usuarios.id == token_db.usuario_id)
    usuario_db = session.exec(statementUsuario).first()
    return usuario_db

async def verificar_admin(usuarioActual: Usuarios = Depends(validarToken)):
    if usuarioActual.rol != "admin":
       raise HTTPException(status_code = 403, detail = "acceso denegado, solo administradores.")
    return usuarioActual


#Rutas solo para administradores

@router.post("/admin/generar-token")
async def generar_token(session: Session = Depends(get_Session), admin : Usuarios = Depends(verificar_admin)):
    nuevo_token = secrets.token_hex(25)

#se guarda quién creo el token.

    nuevoToken_db = Tokens(token = nuevo_token, activo = True, creado_por_id = admin.id)

    session.add(nuevoToken_db)
    session.commit()

    return {"mensaje": "token generado", "token": nuevo_token}


@router.put("/admin/ligar-token")
async def ligarToken(token : str, usuario_id : int, session : Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):
    statement = select(Tokens).where(Tokens.token == token)
    token_db = session.exec(statement).first()

    if not token_db:
        raise HTTPException(status_code = 404, detail = "Token no encontrado")

    # Si usuario_id no está vacío, significa que ya tiene dueño
    if token_db.usuario_id is not None:
        raise HTTPException(
            status_code = 400,detail = f"Error: Este token ya está asignado al usuario con ID {token_db.usuario_id}. Genera uno nuevo."
        )

    statement_usuario = select(Usuarios).where(Usuarios.id == usuario_id)
    usuario_db = session.exec(statement_usuario).first()

    if not usuario_db:
        raise HTTPException(status_code = 404, detail = "Usuario no encontrado.")

    # Si pasa las validaciones, lo ligamos
    token_db.usuario_id = usuario_db.id
    session.add(token_db)
    session.commit()
    return {"mensaje": f"token ligado exitosamente a {usuario_db.username}"}

@router.put("/admin/estado-token")
async def cambiarEstadoToken(
    token: str,
    activar: bool,
    session: Session = Depends(get_Session),
    admin: Usuarios = Depends(verificar_admin),
    token_actual: str = Depends(header_scheme)):
    if token == token_actual and activar == False:
        raise HTTPException(
            status_code=400,
            detail="Seguridad: No puedes dar de baja el token que estás utilizando actualmente."
        )

    statement = select(Tokens).where(Tokens.token == token)
    token_db = session.exec(statement).first()

    if not token_db:
       raise HTTPException(status_code = 404, detail = "Token no encontrado")

    token_db.activo = activar
    session.add(token_db)
    session.commit()
    estado = "ALTA" if activar else "BAJA"
    return {"Mensaje": f"el token ha sido dado de {estado}"}

#lee los tokens
@router.get("/admin/tokens")
async def obtener_todos_los_tokens(session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):

    lista_tokens = session.exec(select(Tokens)).all()

    resultado = []
    for t in lista_tokens:
        resultado.append({
            "id": t.id,
            "token": t.token,
            "activo": t.activo,
            "usuario_id_asignado": t.usuario_id,
            "creado_por_admin_id": t.creado_por_id
        })

    return {"Total_de_Tokens": len(resultado), "Lista_Tokens": resultado}

#CRUD para la tabla de usuarios.
#crear un usuario.
@router.post("/admin/usuarios")
async def crear_usuario_admin(username: str, password: str, rol: str = "usuario", session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin) ):
    statement = select(Usuarios).where(Usuarios.username == username)
    usuario_existente = session.exec(statement).first()

    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este nombre de usuario ya está registrado.")

    nuevo_usuario = Usuarios(username=username, password=password, rol=rol)
    session.add(nuevo_usuario)
    session.commit()
    session.refresh(nuevo_usuario)

    return {
        "mensaje": f"Usuario creado exitosamente por {admin.username}",
        "usuario": {
            "id": nuevo_usuario.id,
            "username": nuevo_usuario.username,
            "rol": nuevo_usuario.rol
        }
    }

#leer todos los registros
@router.get("/admin/usuarios")
async def obtener_todos_los_usuarios(session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):
    lista_usuarios = session.exec(select(Usuarios)).all()

    resultado = [
        {"id": u.id, "username": u.username, "rol": u.rol}
        for u in lista_usuarios
    ]

    return {"Total": len(resultado), "Usuarios": resultado}

#leer solo un registro
@router.get("/admin/usuarios/{usuario_id}")
async def obtener_un_usuario(usuario_id: int, session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):
    usuario_db = session.get(Usuarios, usuario_id)
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {
        "id": usuario_db.id,
        "username": usuario_db.username,
        "rol": usuario_db.rol
    }
#actualizar
@router.put("/admin/usuarios/{usuario_id}")
async def actualizar_usuario(usuario_id: int, nuevo_rol: str = None, nueva_password: str = None,session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):
    usuario_db = session.get(Usuarios, usuario_id)
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if nuevo_rol:
        usuario_db.rol = nuevo_rol

    if nueva_password:
        usuario_db.password = nueva_password

    session.add(usuario_db)
    session.commit()
    session.refresh(usuario_db)

    return {"mensaje": f"Usuario {usuario_db.username} actualizado correctamente"}
#delete
@router.delete("/admin/usuarios/{usuario_id}")
async def eliminar_usuario(usuario_id: int, session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):
    usuario_db = session.get(Usuarios, usuario_id)
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if usuario_db.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta de administrador.")

    session.delete(usuario_db)
    session.commit()

    return {"mensaje": f"El usuario {usuario_db.username} ha sido eliminado de la base de datos."}


#APIS.
@router.get("/admin/apis")
async def obtener_apis(session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):
    apis = session.exec(select(ProveedoresAPI)).all()
    return {"apis": apis}

@router.post("/admin/apis")
async def crear_api(api_data: ProveedoresAPI, session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):
    session.add(api_data)
    try:
        session.commit()
        return {"mensaje": f"API '{api_data.nombre}' registrada exitosamente"}
    except Exception:
        raise HTTPException(status_code=400, detail="Error al guardar. ¿El nombre ya existe?")

@router.delete("/admin/apis/{api_id}")
async def borrar_api(api_id: int, session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):
    api_db = session.exec(select(ProveedoresAPI).where(ProveedoresAPI.id == api_id)).first()
    if not api_db:
        raise HTTPException(status_code=404, detail="API no encontrada")

    session.delete(api_db)
    session.commit()
    return {"mensaje": "API eliminada permanentemente"}

@router.put("/admin/apis/{api_id}/estado")
async def cambiar_estado_api(api_id: int, activar: bool, session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):
    api_db = session.exec(select(ProveedoresAPI).where(ProveedoresAPI.id == api_id)).first()
    if not api_db:
        raise HTTPException(status_code=404, detail="API no encontrada")

    api_db.activa = activar
    session.add(api_db)
    session.commit()
    estado = "Activada" if activar else "Desactivada"
    return {"mensaje": f"API {estado}"}

@router.put("/admin/apis/{api_id}")
async def actualizar_api_completa(api_id: int, api_data: ProveedoresAPI, session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):
    api_db = session.exec(select(ProveedoresAPI).where(ProveedoresAPI.id == api_id)).first()
    if not api_db:
        raise HTTPException(status_code=404, detail="API no encontrada")

    api_db.nombre = api_data.nombre
    api_db.url_base = api_data.url_base
    api_db.api_key = api_data.api_key
    api_db.parametro_num = api_data.parametro_num
    api_db.parametro_key = api_data.parametro_key
    api_db.llave_validacion = api_data.llave_validacion
    api_db.llave_numero = api_data.llave_numero
    api_db.llave_pais = api_data.llave_pais
    api_db.llave_tipo = api_data.llave_tipo
    api_db.valor_celular = api_data.valor_celular
    api_db.llave_codigo = api_data.llave_codigo
    api_db.llave_company = api_data.llave_company

    session.add(api_db)
    try:
        session.commit()
        return {"mensaje": "API actualizada correctamente"}
    except Exception:
        raise HTTPException(status_code=400, detail="Error al actualizar. ¿El nombre ya existe?")

#apartado para numeraciones locales, cargadas a tráves de un csv.
@router.post("/admin/actualizar-bd")
async def actualizar_bd( file: UploadFile = File(...), session: Session = Depends(get_Session), admin: Usuarios = Depends(verificar_admin)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser formato CSV")
    
    try:
        content = await file.read()
        decoded = content.decode('utf-8')
        reader = csv.reader(io.StringIO(decoded))
        next(reader)
        
        nuevos_registros = []
        for row in reader:
            try:
                nuevo = Numeraciones(
                    zona=row[0],
                    numeracion_inicial=int(row[1]),
                    numeracion_final=int(row[2]),
                    ocupacion=row[3],
                    modalidad=row[4],
                    proveedor=row[5],
                    fecha_asignacion=row[6] if len(row) > 6 else None
                )
                nuevos_registros.append(nuevo)
            except Exception:
                pass 
                
        #Inserción
        session.add_all(nuevos_registros)
        session.commit()
        return {"status": "success", "mensaje": f"Se insertaron {len(nuevos_registros)} rangos numéricos correctamente."}
        
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar el CSV: {str(e)}")
    

router = APIRouter(prefix="/auth", tags=["Login 2FA"])

# Esquema para recibir los datos del front
class GenerateOTPRequest(BaseModel):
    username: str
    password: str
    captchaToken: str

@router.post("/generate")
async def generate_otp(credentials: GenerateOTPRequest, session: Session = Depends(get_Session)):
    
    # 1. Validar que no sea un bot
    is_human = await recaptchaService.verify(credentials.captchaToken)
    if not is_human:
        raise HTTPException(status_code=400, detail="Validación de reCAPTCHA fallida.")

    # 2. Validar credenciales
    statement = select(Usuarios).where(Usuarios.username == credentials.username)
    user_db = session.exec(statement).first()

    if not user_db or user_db.password != credentials.password:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrecta.")

    # 3. Generar código y hashearlo
    plain_otp = securityUtil.generate_otp(user_db.otp_length, user_db.otp_type)
    hashed_otp = securityUtil.hash_code(plain_otp)

    # 4. Invalidar códigos viejos
    old_codes_stmt = select(TwoFactorCodes).where(
        TwoFactorCodes.usuario_id == user_db.id, 
        TwoFactorCodes.is_used == False
    )
    for code in session.exec(old_codes_stmt).all():
        code.is_used = True

    # 5. Guardar nuevo código
    nuevo_codigo = TwoFactorCodes(usuario_id=user_db.id, hashed_code=hashed_otp)
    session.add(nuevo_codigo)
    session.commit()

    # (Aquí iría el envío real del correo/SMS en el futuro)
    print(f"DEBUG - Código OTP (No mostrar en prod): {plain_otp}") 

    # 6. Devolver la pista
    return {
        "mensaje": "Código de verificación generado y enviado.",
        "destinator_hint": securityUtil.mask_email(user_db.email)
    }

class VerifyOTPRequest(BaseModel):
    user_id: int  # Usamos user_id porque así lo pide la documentación del POST
    otp_code: str

@router.post("/2fa/verify")
async def verify_otp(request: VerifyOTPRequest, session: Session = Depends(get_Session)):
    # Pasamos el user_id de la petición al servicio
    result = authService.verify_2fa_code(session, request.user_id, request.otp_code)
    
    return result