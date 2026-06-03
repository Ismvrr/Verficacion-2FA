from datetime import datetime
import os
from sqlmodel import Session
from Repositories import twoFactorRepo
from Utils import securityUtil, jwtUtil

OTP_MAX_ATTEMPTS = int(os.getenv("otpMaxAttempts", 3))

def verify_2fa_code(session: Session, usuario_id: int, otp_code: str) -> dict:
    try:
        otp_record = twoFactorRepo.get_latest_otp(session, usuario_id)
        
        # Validar que exista y no esté usado
        if not otp_record or otp_record.is_used:
            return {"errorCode": 201, "status": "ERROR", "errorMessage": "Código ingresado incorrecto."}
            
        # Validar expiración (comparando contra datetime.utcnow() porque tu compañero usó utcnow en expires_at)
        if datetime.utcnow() > otp_record.expires_at:
            return {"errorCode": 202, "status": "ERROR", "errorMessage": "Código OTP expirado."}
            
        # Validar límite de intentos
        if otp_record.attempts >= OTP_MAX_ATTEMPTS:
            return {"errorCode": 203, "status": "ERROR", "errorMessage": "Máximo de intentos permitidos excedido."}
            
        # Verificar que el código ingresado coincida (Ojo: usamos otp_record.hashed_code)
        is_valid = securityUtil.verify_otp_hash(otp_code, otp_record.hashed_code)
        
        if not is_valid:
            twoFactorRepo.increment_attempts(session, otp_record)
            return {"errorCode": 201, "status": "ERROR", "errorMessage": "Código ingresado incorrecto."}
            
        # Éxito: Marcar como usado y generar JWT
        twoFactorRepo.mark_as_used(session, otp_record)
        token = jwtUtil.create_access_token(usuario_id)
        
        return {
            "errorCode": 0,
            "status": "SUCCESS",
            "errorMessage": "OK",
            "access_token": token
        }
        
    except Exception as e:
        print(f"Error en validación 2FA: {e}")
        return {"errorCode": 500, "status": "ERROR", "errorMessage": "Error interno del servidor."}