from datetime import datetime
import os
from sqlmodel import Session
from Repositories import twoFactorRepo
from Utils import securityUtil, jwtUtil

OTP_MAX_ATTEMPTS = int(os.getenv("otpMaxAttempts", 3))

def verify_2fa_code(session: Session, user_id: int, otp_code: str) -> dict:
    try:
        otp_record = twoFactorRepo.get_latest_otp(session, user_id)

        if not otp_record or otp_record.is_used:
            return {"errorCode": 201, "status": "ERROR", "errorMessage": "El c\xf3digo ingresado es incorrecto. Verifique e intente nuevamente.", "access_token": None}

        if datetime.utcnow() > otp_record.expires_at:
            return {"errorCode": 202, "status": "ERROR", "errorMessage": "El c\xf3digo OTP ha expirado. Deber\xe1 iniciar sesi\xf3n nuevamente para generar uno nuevo.", "access_token": None}

        if otp_record.attempts >= OTP_MAX_ATTEMPTS:
            return {"errorCode": 203, "status": "ERROR", "errorMessage": "Se ha excedido el n\xfamero m\xe1ximo de intentos permitidos. Por seguridad, solicite un nuevo c\xf3digo.", "access_token": None}

        is_valid = securityUtil.verify_otp_hash(otp_code, otp_record.code_hash)

        if not is_valid:
            twoFactorRepo.increment_attempts(session, otp_record)
            return {"errorCode": 201, "status": "ERROR", "errorMessage": "El c\xf3digo ingresado es incorrecto. Verifique e intente nuevamente.", "access_token": None}

        twoFactorRepo.mark_as_used(session, otp_record)
        token = jwtUtil.create_access_token(user_id)

        return {
            "errorCode": 0,
            "status": "SUCCESS",
            "errorMessage": "OK",
            "access_token": token
        }

    except Exception as e:
        print(f"Error en validaci\xf3n 2FA: {e}")
        return {"errorCode": 500, "status": "ERROR", "errorMessage": "Ocurri\xf3 un error interno al validar el c\xf3digo. Por favor, contacte a soporte.", "access_token": None}