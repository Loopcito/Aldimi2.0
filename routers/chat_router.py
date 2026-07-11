from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from services.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()

class ChatRequest(BaseModel):
    session_id: str = Field(..., example="sesion_prueba_1")
    message: str = Field(..., example="Hola, ¿cuáles son las preguntas frecuentes?")
    usuario_tipo: str = Field(
        ..., 
        example="Voluntario", 
        description="Roles válidos: Voluntario, Padres de Familia, Administrador, Personal de apoyo"
    )

@router.post("/api/chat")
async def interactuar_chat(request: ChatRequest):
    try:
        respuesta = chat_service.responder_con_contexto(
            session_id=request.session_id,
            mensaje_usuario=request.message,
            usuario_tipo=request.usuario_tipo
        )
        return {"response": respuesta}
        
    except Exception as e:
        print(f"❌ Error crítico en el endpoint de chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")