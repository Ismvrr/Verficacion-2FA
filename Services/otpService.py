from Utils import securityUtil

def generate_otp(length: int, otp_type: int) -> str:
    otp_type_str = "numeric" if otp_type == 1 else "alphanumeric"
    return securityUtil.generate_otp(length, otp_type_str)
