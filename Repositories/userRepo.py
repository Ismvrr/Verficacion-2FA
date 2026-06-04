from sqlmodel import Session, select
from Models.models import Usuarios

def get_user_by_username(session: Session, username: str) -> Usuarios | None:
    stmt = select(Usuarios).where(Usuarios.username == username)
    return session.exec(stmt).first()

def get_user_by_id(session: Session, user_id: int) -> Usuarios | None:
    return session.get(Usuarios, user_id)

def update_user_config(session: Session, user_id: int, length: int, otp_type: int, method: int) -> Usuarios | None:
    user = session.get(Usuarios, user_id)
    if not user:
        return None
    user.two_factor_length = length
    user.two_factor_type = otp_type
    user.two_factor_method = method
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
