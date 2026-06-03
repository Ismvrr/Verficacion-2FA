from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from Config.db import SessionDep, get_Session
from Models.models import Telefonos, Usuarios, ProveedoresAPI,Numeraciones, Solicitud
from .auth import validarToken
import httpx

router = APIRouter(prefix="/telefonos", tags=["Validacion"])

async def consultar_api_dinamica(numero: str, proveedor: ProveedoresAPI) -> dict | None:
    params = {
        proveedor.parametro_key: proveedor.api_key
    }

    url_final = proveedor.url_base
    if "{numero}" in url_final:
        url_final = url_final.replace("{numero}", numero)
    else:
        params[proveedor.parametro_num] = numero

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url_final, params=params)
        data = resp.json()

        print(f"Respuesta de {proveedor.nombre}: ", data)

        if data.get(proveedor.llave_validacion):

            tipo_recibido = str(data.get(proveedor.llave_tipo)).lower()
            es_celular = tipo_recibido == proveedor.valor_celular.lower()

            return {
                "numero": data.get(proveedor.llave_numero) or numero,
                "pais": data.get(proveedor.llave_pais) or "Desconocido",
                "tipo": "Celular" if es_celular else "Fijo",
                "codigo_pais": data.get(proveedor.llave_codigo) or "N/A",
                "compañia": data.get(proveedor.llave_company) or "Desconocida",
                "api_Utilizada": proveedor.nombre
            }
    except Exception as e:
        print(f"Error interno con la API {proveedor.nombre}: {e}")

    return None

@router.post("/Verificar/{numero}")
async def verificar_numero(numero: str, api: str = Query("auto"), session: Session = Depends(get_Session), usuarioActual: Usuarios = Depends(validarToken)):

    # CASO 03 (Local): Si lo encuentra en la BD local (Cache)
    db_tel = session.exec(select(Telefonos).where(Telefonos.numero == numero)).first()
    if db_tel:
        return {
            "status": "success",
            "data": {
                "statuscode": "03",
                "telefono": db_tel.numero,
                "zona": db_tel.pais,
                "tipo": db_tel.tipo,
                "Proveedor": db_tel.compañia,
                "mensaje": "Recuperado de la base de datos local"
            }
        }

    datos_tel = None

    apis_activas = session.exec(select(ProveedoresAPI).where(ProveedoresAPI.activa == True)).all()

    if not apis_activas:
        raise HTTPException(status_code=500, detail="No hay APIs configuradas ni encendidas en el sistema.")

    if api == "auto":
        for proveedor in apis_activas:
            print(f"Probando dinámicamente con: {proveedor.nombre}")
            datos_tel = await consultar_api_dinamica(numero, proveedor)
            if datos_tel:
                break
    else:

        proveedor_elegido = next((p for p in apis_activas if p.nombre.lower() == api.lower()), None)
        if proveedor_elegido:
            datos_tel = await consultar_api_dinamica(numero, proveedor_elegido)
        else:
            raise HTTPException(status_code=404, detail=f"La API '{api}' no está registrada o está apagada.")

    # CASO 02: Si ninguna API activa lo encontró
    if not datos_tel:
        return {
            "status": "success",
            "data": {
                "statuscode": "02",
                "telefono": numero,
                "mensaje": "número inválido."
            }
        }

    nuevo_tel = Telefonos(
        numero=datos_tel["numero"].replace("+", ""),
        pais=datos_tel["pais"],
        tipo=datos_tel["tipo"],
        codigo_pais=datos_tel["codigo_pais"],
        compañia=datos_tel["compañia"],
        api_Utilizada=datos_tel["api_Utilizada"]
    )

    session.add(nuevo_tel)
    session.commit()
    session.refresh(nuevo_tel)

    # CASO 01: Éxito con API Externa
    return {
        "status": "success",
        "data": {
            "statuscode": "01",
            "telefono": nuevo_tel.numero,
            "zona": nuevo_tel.pais,
            "tipo": nuevo_tel.tipo,
            "Proveedor": nuevo_tel.compañia
        }
    }

#Auxiliares para el frontend
@router.get("/", response_model=list[Telefonos])
def leerTelefono(Session: SessionDep, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100):
    telefonos = Session.exec(select(Telefonos).offset(offset).limit(limit)).all()
    return telefonos

@router.get("/apis_activas")
def obtener_apis_activas(session: Session = Depends(get_Session), usuarioActual: Usuarios = Depends(validarToken)):
    apis = session.exec(select(ProveedoresAPI).where(ProveedoresAPI.activa == True)).all()
    return [api.nombre for api in apis]

#Búsqueda en cátalogo de México.
@router.post("/telefono", summary="Buscar número en catálogo local de México", tags=["Validacion"])
def buscar_local(data: Solicitud, session: Session = Depends(get_Session), usuarioActual: Usuarios = Depends(validarToken)):
    telefono = data.telefono 
    
    if not telefono.startswith("52"):
        return {"status" : "success", "data": {"statuscode": "03", "telefono": telefono, "mensaje": "Teléfono perteneciente a otro país"}}

    try:
        prefijo = int(telefono[2:])
    except ValueError:
        return {"status": "success", "data": {"statuscode": "02", "telefono": telefono, "mensaje": "Formato numérico inválido"}}
    
    query = select(Numeraciones).where(
        Numeraciones.numeracion_inicial <= prefijo,
        Numeraciones.numeracion_final >= prefijo
    )
    info_tel = session.exec(query).first()

    if not info_tel:
        return {"status": "success", "data": {"statuscode": "02", "telefono": telefono, "mensaje": "Número inválido"}}
    
    tipo = "Móvil" if info_tel.modalidad in ("MPP", "CPP") else "Fijo"
    
    db_tel = session.exec(select(Telefonos).where(Telefonos.numero == telefono)).first()
    
    if not db_tel:
        nuevo_tel = Telefonos(
            numero=telefono,
            pais="Mexico", # O puedes poner info_tel.zona si prefieres
            tipo=tipo,
            codigo_pais="52",
            compañia=info_tel.proveedor,
            api_Utilizada="API Mexico" 
        )
        session.add(nuevo_tel)
        session.commit()

    return {
        "status": "success",
        "data": {
            "statuscode": "01",
            "telefono": telefono,
            "zona": info_tel.zona,
            "modalidad": info_tel.modalidad,
            "tipo": tipo,
            "Proveedor": info_tel.proveedor
        }
    }