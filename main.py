import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importamos los routers que creamos en la fase anterior
from routers import chat_router, data_router

# Inicializamos la aplicación de FastAPI con metadatos para tu presentación
app = FastAPI(
    title="ALDIMI-Assist API",
    description="Backend modular de Inteligencia Artificial para la gestión del Albergue Divina Misericordia",
    version="1.0.0"
)

# =========================================================================
# CONFIGURACIÓN DE CORS (Crucial para conectar con el Frontend)
# =========================================================================
# Esto evita el famoso error de "CORS Policy" cuando el frontend de tu compañero
# intente hacer peticiones HTTP a tu backend desde otro puerto o dominio local.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite conexiones desde cualquier origen en desarrollo
    allow_credentials=True,
    allow_methods=["*"], # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"], # Permite todas las cabeceras
)

# =========================================================================
# INCLUSIÓN DE COMPONENTES MODULARES (Routers)
# =========================================================================
app.include_router(chat_router.router)
app.include_router(data_router.router)

# =========================================================================
# ENDPOINT DE CONTROL / HEALTH CHECK
# =========================================================================
@app.get("/", tags=["Root"])
def root():
    """Endpoint de bienvenida para verificar que el servidor está encendido correctamente"""
    return {
        "status": "online",
        "proyecto": "ALDIMI-Assist",
        "mensaje": "El servidor de FastAPI está corriendo y listo para procesar solicitudes de IA."
    }

# Código para permitir la ejecución directa con 'python main.py' si se desea
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)