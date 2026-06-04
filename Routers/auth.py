import jwt as pyjwt
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import APIKeyHeader
from sqlmodel import Session, select
from passlib.context import CryptContext
from Config.db import get_Session
from Models.models import Usuarios, TwoFactorCodes, Tokens
from Utils import securityUtil
from Services import recaptchaService, authService, otpService


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/auth", tags=["Login 2FA"])

header_scheme = APIKeyHeader(name="Authorization")

async def validarToken(token: str = Depends(header_scheme), session: Session = Depends(get_Session)):
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


def get_current_user_id(authorization: str = Header(None)) -> int:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token requerido")
    token = authorization.replace("Bearer ", "")
    try:
        import os
        secret = os.getenv("JWT_SECRET", os.getenv("jwtSecret", "tu_clave_secreta_por_defecto"))
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


class GenerateOTPRequest(BaseModel):
    username: str
    password: str
    grecaptchaToken: str

@router.post("/login")
async def login_dashboard(username: str, password: str, session: Session = Depends(get_Session)):
    statement = select(Usuarios).where(Usuarios.username == username)
    user_db = session.exec(statement).first()
    if not user_db or not pwd_context.verify(password, user_db.password):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrecta.")
    if not user_db.two_factor_enabled:
        statementToken = select(Tokens).where(Tokens.usuario_id == user_db.id, Tokens.activo == True)
        token_db = session.exec(statementToken).first()
        if not token_db:
            raise HTTPException(status_code=403, detail="No tienes un token asignado.")
        return {"errorCode": 0, "status": "SUCCESS", "token": token_db.token}
    plain_otp = otpService.generate_otp(user_db.two_factor_length, user_db.two_factor_type)
    hashed_otp = securityUtil.hash_code(plain_otp)
    stmt = select(TwoFactorCodes).where(TwoFactorCodes.user_id == user_db.id, TwoFactorCodes.is_used == False)
    for code in session.exec(stmt).all():
        code.is_used = True
    session.commit()
    hint = securityUtil.mask_email(user_db.email)
    nuevo_codigo = TwoFactorCodes(user_id=user_db.id, code_hash=hashed_otp, code_destinator=hint)
    session.add(nuevo_codigo)
    session.commit()
    print(f"DEBUG - Código OTP (No mostrar en prod): {plain_otp}")
    result = {"errorCode": 0, "status": "2FA_REQUIRED", "errorMessage": "OK", "user_id": user_db.id, "destinator_hint": hint}
    if not recaptchaService.RECAPTCHA_SECRET:
        result["dev_otp"] = plain_otp
    return result

class VerifyOTPRequest(BaseModel):
    user_id: int
    otp_code: str

@router.post("/verify-and-enter")
async def verify_and_enter(request: VerifyOTPRequest, session: Session = Depends(get_Session)):
    result = authService.verify_2fa_code(session, request.user_id, request.otp_code)
    if result["errorCode"] != 0:
        return result
    statementToken = select(Tokens).where(Tokens.usuario_id == request.user_id, Tokens.activo == True)
    token_db = session.exec(statementToken).first()
    if not token_db:
        return {"errorCode": 500, "status": "ERROR", "errorMessage": "No tienes un token asignado.", "access_token": None}
    return {"errorCode": 0, "status": "SUCCESS", "errorMessage": "OK", "token": token_db.token}

@router.post("/generate")
async def generate_otp(credentials: GenerateOTPRequest, session: Session = Depends(get_Session)):
    try:
        is_human = await recaptchaService.verify(credentials.grecaptchaToken)
        if not is_human:
            return {
                "errorCode": 102,
                "status": "ERROR",
                "errorMessage": "No se pudo validar el reCAPTCHA. Por favor, intente de nuevo.",
                "user_id": None,
                "destinator_hint": None
            }

        statement = select(Usuarios).where(Usuarios.username == credentials.username)
        user_db = session.exec(statement).first()

        if not user_db or not pwd_context.verify(credentials.password, user_db.password):
            return {
                "errorCode": 101,
                "status": "ERROR",
                "errorMessage": "Usuario o contrase\xf1a incorrectos.",
                "user_id": None,
                "destinator_hint": None
            }

        if not user_db.two_factor_enabled:
            from Utils import jwtUtil
            token = jwtUtil.create_access_token(user_db.id)
            return {
                "errorCode": 0,
                "status": "2FA_DISABLED",
                "errorMessage": "2FA desactivado, acceso directo.",
                "user_id": user_db.id,
                "destinator_hint": None,
                "access_token": token
            }

        plain_otp = otpService.generate_otp(user_db.two_factor_length, user_db.two_factor_type)
        hashed_otp = securityUtil.hash_code(plain_otp)

        stmt = select(TwoFactorCodes).where(
            TwoFactorCodes.user_id == user_db.id,
            TwoFactorCodes.is_used == False
        )
        for code in session.exec(stmt).all():
            code.is_used = True
        session.commit()

        hint = securityUtil.mask_email(user_db.email)
        nuevo_codigo = TwoFactorCodes(
            user_id=user_db.id,
            code_hash=hashed_otp,
            code_destinator=hint
        )
        session.add(nuevo_codigo)
        session.commit()

        print(f"DEBUG - C\xf3digo OTP (No mostrar en prod): {plain_otp}")

        result = {
            "errorCode": 0,
            "status": "2FA_REQUIRED",
            "errorMessage": "OK",
            "user_id": user_db.id,
            "destinator_hint": hint
        }

        if not recaptchaService.RECAPTCHA_SECRET:
            result["dev_otp"] = plain_otp

        return result

    except Exception as e:
        print(f"Error en generate: {e}")
        return {
            "errorCode": 500,
            "status": "ERROR",
            "errorMessage": "Ocurrio un error interno al procesar su solicitud de inicio de sesi\xf3n.",
            "user_id": None,
            "destinator_hint": None
        }


@router.post("/2fa/verify")
async def verify_otp(request: VerifyOTPRequest, session: Session = Depends(get_Session)):
    result = authService.verify_2fa_code(session, request.user_id, request.otp_code)
    return result


class UpdateConfigRequest(BaseModel):
    two_factor_length: int
    two_factor_type: int
    two_factor_method: int

@router.put("/user/config")
async def update_user_config(
    config: UpdateConfigRequest,
    session: Session = Depends(get_Session),
    user_id: int = Depends(get_current_user_id)
):
    from Repositories import userRepo
    user = userRepo.update_user_config(session, user_id, config.two_factor_length, config.two_factor_type, config.two_factor_method)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {
        "errorCode": 0,
        "status": "SUCCESS",
        "errorMessage": "Configuraci\xf3n actualizada correctamente.",
        "config": {
            "two_factor_length": user.two_factor_length,
            "two_factor_type": user.two_factor_type,
            "two_factor_method": user.two_factor_method
        }
    }


@router.get("/user/config")
async def get_user_config(
    session: Session = Depends(get_Session),
    user_id: int = Depends(get_current_user_id)
):
    from Repositories import userRepo
    user = userRepo.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {
        "errorCode": 0,
        "status": "SUCCESS",
        "errorMessage": "OK",
        "config": {
            "two_factor_length": user.two_factor_length,
            "two_factor_type": user.two_factor_type,
            "two_factor_method": user.two_factor_method
        }
    }


@router.get("/user/config-dashboard")
async def get_user_config_dashboard(
    session: Session = Depends(get_Session),
    user: Usuarios = Depends(validarToken)
):
    from Repositories import userRepo
    u = userRepo.get_user_by_id(session, user.id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {
        "errorCode": 0,
        "status": "SUCCESS",
        "errorMessage": "OK",
        "config": {
            "two_factor_length": u.two_factor_length,
            "two_factor_type": u.two_factor_type,
            "two_factor_method": u.two_factor_method,
            "two_factor_enabled": u.two_factor_enabled
        }
    }


class UpdateConfigDashboardRequest(BaseModel):
    two_factor_enabled: bool = True
    two_factor_length: int = 6
    two_factor_type: int = 1
    two_factor_method: int = 2

@router.put("/user/config-dashboard")
async def update_user_config_dashboard(
    config: UpdateConfigDashboardRequest,
    session: Session = Depends(get_Session),
    user: Usuarios = Depends(validarToken)
):
    from Repositories import userRepo
    u = userRepo.update_user_config(session, user.id, config.two_factor_length, config.two_factor_type, config.two_factor_method)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    u.two_factor_enabled = config.two_factor_enabled
    session.add(u)
    session.commit()
    return {
        "errorCode": 0,
        "status": "SUCCESS",
        "errorMessage": "Configuraci\xf3n actualizada correctamente.",
        "config": {
            "two_factor_length": u.two_factor_length,
            "two_factor_type": u.two_factor_type,
            "two_factor_method": u.two_factor_method,
            "two_factor_enabled": u.two_factor_enabled
        }
    }