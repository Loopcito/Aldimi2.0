from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
# Importamos la lógica que escribimos en services/chat_service.py
from services.chat_service import ChatService

# Inicializamos el router para agrupar estos endpoints
router = APIRouter(
    prefix="/api/chat",
    tags=["Chatbot Core"]
)

# Instanciamos el servicio de chat una sola vez de forma global en este archivo
chat_service = ChatService()

# =========================================================================
# SQUEMA DE VALIDACIÓN DE DATOS (Pydantic)
# =========================================================================
class ChatRequest(BaseModel):
    session_id: str
    message: str

# =========================================================================
# ENDPOINT POST: ENVIAR MENSAJE AL CHATBOT
# =========================================================================
@router.post("")
def procesar_mensaje_chat(request: ChatRequest):
    """
    Endpoint principal del Chatbot ALDIMI-Assist.
    Recibe el identificador de la sesión y el mensaje del usuario,
    procesa el contexto en MongoDB, consulta a Groq y devuelve la respuesta de la IA.
    """
    # Validación simple para evitar strings vacíos
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")
    
    if not request.session_id.strip():
        raise HTTPException(status_code=400, detail="Se requiere un session_id válido para mantener la memoria.")

    # Ejecutamos el servicio conversacional completo
    respuesta_ia = chat_service.responder_con_contexto(
        session_id=request.session_id,
        mensaje_usuario=request.message
    )
    
    # Retornamos la respuesta en un formato JSON estándar que el frontend leerá fácilmente
    return {
        "session_id": request.session_id,
        "response": respuesta_ia
    }