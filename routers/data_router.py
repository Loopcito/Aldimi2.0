from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date
from config.db import get_postgres_conn
from services.sentiment_service import SentimentService

router = APIRouter(
    prefix="/api/data",
    tags=["Gestión de Datos y NLP"]
)

# Instanciamos el servicio de análisis de sentimiento
sentiment_service = SentimentService()

# =========================================================================
# MODELOS DE VALIDACIÓN (Pydantic) - Alineados con el Contrato de Interfaz
# =========================================================================

class DniRequest(BaseModel):
    num_dni: str
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    direccion: str

class DonacionRequest(BaseModel):
    fecha_donacion: date
    monto: float
    bien_donado: str
    cantidad: int
    donante_nombre: str

class RecetaRequest(BaseModel):
    paciente_nombre: str
    medicamento: str
    dosis: str
    frecuencia: str
    fecha_emision: date
    indicaciones: str

class ReporteRequest(BaseModel):
    paciente_nombre: str
    texto_reporte: str
    fecha_reporte: date

# =========================================================================
# ENDPOINTS DE REGISTRO (Inserciones directas en PostgreSQL)
# =========================================================================

@router.post("/dni")
def registrar_dni(data: DniRequest):
    """Guarda los datos extraídos del DNI en PostgreSQL"""
    conn = get_postgres_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión con la base de datos relacional.")
    
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO dni_master (num_dni, nombres, apellidos, fecha_nacimiento, direccion)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (num_dni) DO NOTHING;
        """
        cursor.execute(query, (data.num_dni, data.nombres, data.apellidos, data.fecha_nacimiento, data.direccion))
        conn.commit()
        cursor.close()
        return {"status": "success", "message": "Datos de DNI procesados correctamente."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al insertar en la base de datos: {e}")
    finally:
        conn.close()

@router.post("/donacion")
def registrar_donacion(data: DonacionRequest):
    """Guarda las boletas de donaciones (bienes o efectivo)"""
    conn = get_postgres_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión con la base de datos.")
    
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO control_donaciones (fecha_donacion, monto, bien_donado, cantidad, donante_nombre)
            VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(query, (data.fecha_donacion, data.monto, data.bien_donado, data.cantidad, data.donante_nombre))
        conn.commit()
        cursor.close()
        return {"status": "success", "message": "Donación registrada exitosamente."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al registrar donación: {e}")
    finally:
        conn.close()

@router.post("/receta")
def registrar_receta(data: RecetaRequest):
    """Guarda las recetas médicas extraídas por el OCR"""
    conn = get_postgres_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión con la base de datos.")
    
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO recetas_medicas (paciente_nombre, medicamento, dosis, frecuencia, fecha_emision, indicaciones)
            VALUES (%s, %s, %s, %s, %s, %s);
        """
        cursor.execute(query, (data.paciente_nombre, data.medicamento, data.dosis, data.frecuencia, data.fecha_emision, data.indicaciones))
        conn.commit()
        cursor.close()
        return {"status": "success", "message": "Receta médica guardada con éxito."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al guardar receta: {e}")
    finally:
        conn.close()

# =========================================================================
# ENDPOINT NLP: REPORTE DE EVOLUCIÓN + ANÁLISIS DE SENTIMIENTO AUTOMÁTICO
# =========================================================================
@router.post("/reporte")
def registrar_reporte_con_nlp(data: ReporteRequest):
    """
    Recibe la nota de evolución, invoca el SentimentService (Groq Llama 3 LLM)
    para analizar la carga psicológica/médica de manera síncrona y guarda todo el
    resultado consolidado en PostgreSQL.
    """
    if not data.texto_reporte.strip():
        raise HTTPException(status_code=400, detail="El texto del reporte no puede estar vacío.")

    # 1. Ejecutamos el motor de IA en segundo plano para obtener el JSON estricto
    analisis_ia = sentiment_service.analizar_reporte(data.texto_reporte)
    
    sentimiento = analisis_ia.get("sentimiento", "Neutral")
    criticidad = analisis_ia.get("criticidad", 3)

    # 2. Conectamos a Postgres para almacenar el reporte enriquecido
    conn = get_postgres_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Error al conectar con PostgreSQL.")
    
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO reportes_evolucion (paciente_nombre, texto_reporte, fecha_reporte, sentimiento_predicho, nivel_criticidad)
            VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(query, (data.paciente_nombre, data.texto_reporte, data.fecha_reporte, sentimiento, criticidad))
        conn.commit()
        cursor.close()
        
        # Devolvemos un reporte completo para que el frontend pueda pintar alertas visuales inmediatas
        return {
            "status": "success",
            "message": "Reporte clínico analizado y almacenado con éxito.",
            "analisis_nlp": {
                "sentimiento_detectado": sentimiento,
                "nivel_criticidad": criticidad
            }
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error transaccional en el reporte: {e}")
    finally:
        conn.close()