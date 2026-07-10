import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
from dotenv import load_dotenv

# Cargar las variables de entorno del archivo .env
load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL")
MONGO_URL = os.getenv("MONGO_URL")

# =========================================================================
# 1. CONFIGURACIÓN DE POSTGRESQL (Persistencia del OCR y Reportes)
# =========================================================================
def get_postgres_conn():
    """
    Crea y retorna una conexión fresca a PostgreSQL.
    Se usa como función para abrir y cerrar conexiones por cada petición (buena práctica).
    """
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        return conn
    except Exception as e:
        print(f"❌ Error crítico al conectar con PostgreSQL: {e}")
        return None

# =========================================================================
# 2. CONFIGURACIÓN DE MONGODB (Historial de Conversaciones / Logs del Chatbot)
# =========================================================================
try:
    # Inicializamos el cliente de Mongo de forma global
    mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    
    # Seleccionamos la base de datos para el asistente conversacional
    db_mongo = mongo_client["aldimi_nlp_db"]
    
    # Forzar una consulta simple para verificar si el servicio de Mongo está corriendo
    mongo_client.server_info()
    print("✅ Conexión exitosa a MongoDB (aldimi_nlp_db).")
except Exception as e:
    print(f"❌ Error crítico al conectar con MongoDB: {e}")
    db_mongo = None