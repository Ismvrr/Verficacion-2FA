import jwt
import os
from datetime import datetime, timedelta

def create_access_token(usuario_id: int) -> str:
    # Se obtiene la llave secreta del .env
    jwt_secret = os.getenv("jwtSecret", "tu_clave_secreta_por_defecto") 
    
    payload = {
        "sub": str(usuario_id),
        "exp": datetime.utcnow() + timedelta(hours=2) # El token expira en 2 horas
    }
    
    return jwt.encode(payload, jwt_secret, algorithm="HS256")