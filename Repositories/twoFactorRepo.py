from sqlmodel import Session, select
from Models.models import TwoFactorCodes

def get_latest_otp(session: Session, usuario_id: int) -> TwoFactorCodes | None:
    # Ordenamos por id de forma descendente para obtener el último código generado
    statement = select(TwoFactorCodes).where(TwoFactorCodes.usuario_id == usuario_id).order_by(TwoFactorCodes.id.desc())
    return session.exec(statement).first()

def increment_attempts(session: Session, otp_record: TwoFactorCodes):
    otp_record.attempts += 1
    session.add(otp_record)
    session.commit()

def mark_as_used(session: Session, otp_record: TwoFactorCodes):
    otp_record.is_used = True
    session.add(otp_record)
    session.commit()