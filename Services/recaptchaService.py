# services/recaptchaService.py
import os
import httpx
from dotenv import load_dotenv

load_dotenv()
RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET_KEY")

async def verify(token: str) -> bool:
    """Valida el token contra la API de Google."""
    if not token:
        return False
        
    url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {"secret": RECAPTCHA_SECRET, "response": token}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload)
        result = response.json()
        return result.get("success", False)
    except Exception as e:
        print(f"Error reCAPTCHA: {e}")
        return False