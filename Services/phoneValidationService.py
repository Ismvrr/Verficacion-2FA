import phonenumbers
from phonenumbers import carrier, geocoder, PhoneNumberType

def validate_phone_local(numero: str) -> dict | None:
    try:
        numero_limpio = numero.strip().lstrip("+")
        if not numero_limpio.isdigit():
            return None
        numero_con_mas = "+" + numero_limpio
        parsed = phonenumbers.parse(numero_con_mas, None)
        if not phonenumbers.is_valid_number(parsed):
            return None

        country_code = str(parsed.country_code)
        country_name = geocoder.country_name_for_number(parsed, "es")
        if not country_name:
            country_name = geocoder.country_name_for_number(parsed, "en")
        operador = carrier.name_for_number(parsed, "es") or carrier.name_for_number(parsed, "en") or "Desconocida"
        number_type = phonenumbers.number_type(parsed)
        es_movil = number_type in (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE)

        return {
            "numero": numero_limpio,
            "pais": country_name or "Desconocido",
            "tipo": "Celular" if es_movil else "Fijo",
            "codigo_pais": country_code,
            "compañia": operador,
            "api_Utilizada": "Validación Local"
        }
    except Exception:
        return None
