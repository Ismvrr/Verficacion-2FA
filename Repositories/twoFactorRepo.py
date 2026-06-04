from sqlmodel import Session, select
from Models.models import TwoFactorCodes

def get_latest_otp(session: Session, user_id: int) -> TwoFactorCodes | None:
    statement = select(TwoFactorCodes).where(TwoFactorCodes.user_id == user_id).order_by(TwoFactorCodes.id.desc())
    return session.exec(statement).first()

def save_otp(session: Session, otp: TwoFactorCodes):
    session.add(otp)
    session.commit()

def invalidate_previous_otps(session: Session, user_id: int):
    stmt = select(TwoFactorCodes).where(
        TwoFactorCodes.user_id == user_id,
        TwoFactorCodes.is_used == False
    )
    for code in session.exec(stmt).all():
        code.is_used = True
    session.commit()

def increment_attempts(session: Session, otp_record: TwoFactorCodes):
    otp_record.attempts += 1
    session.add(otp_record)
    session.commit()

def mark_as_used(session: Session, otp_record: TwoFactorCodes):
    otp_record.is_used = True
    session.add(otp_record)
    session.commit()