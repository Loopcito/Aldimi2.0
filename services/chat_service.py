import os
from openai import OpenAI
from datetime import datetime
from config.db import db_mongo
from config.db import get_postgres_conn

class ChatService:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("OPENAI_API_BASE"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.model = os.getenv("NLP_MODEL_NAME", "llama-3.1-8b-instant")
        self.history_collection = db_mongo["chat_logs"] if db_mongo is not None else None

    def obtener_total_pacientes_real(self) -> int:
        """Consulta rápidamente PostgreSQL para saber cuántos pacientes reales existen"""
        conn = get_postgres_conn()
        if not conn:
            return 0
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM dni_master;")
            total = cursor.fetchone()[0]
            cursor.close()
            return total
        except Exception as e:
            print(f"⚠️ No se pudo contar los pacientes para el prompt: {e}")
            return 0
        finally:
            conn.close()

    def obtener_historial_contexto(self, session_id: str, limite: int = 6):
        if self.history_collection is None:
            return []
        logs = self.history_collection.find({"session_id": session_id}).sort("timestamp", 1)
        mensajes_contexto = []
        for log in logs:
            mensajes_contexto.append({"role": log["role"], "content": log["content"]})
        return mensajes_contexto[-limite:]

    def guardar_mensaje(self, session_id: str, role: str, content: str):
        if self.history_collection is not None:
            self.history_collection.insert_one({
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow()
            })

    def responder_con_contexto(self, session_id: str, mensaje_usuario: str) -> str:
        cantidad_pacientes = self.obtener_total_pacientes_real()

        # =========================================================================
        # SYSTEM PROMPT ROBUSTO CON PROTOCOLOS DE SEGURIDAD Y RESTRICCIONES
        # =========================================================================
        system_prompt = {
            "role": "system",
            "content": (
                "Eres ALDIMI-Assist, el asistente oficial de Inteligencia Artificial del Albergue Divina Misericordia (ALDIMI).\n"
                "Tu objetivo es ayudar con empatía, profesionalismo y brevedad. Responde siempre en español.\n\n"
                
                f"--- CONTEXTO EN VIVO ---\n"
                f"Actualmente el albergue tiene exactamente {cantidad_pacientes} paciente(s) registrado(s) en el sistema.\n\n"
                
                "--- PROTOCOLOS PRIORITARIOS DE ACTUACIÓN ---\n"
                "1. PROTOCOLO DE EMERGENCIA MÉDICA: Si el usuario menciona síntomas de alerta clínica o palabras como 'fiebre alta', "
                "'convulsión', 'dificultad para respirar', 'sangrado' o cualquier emergencia, DEBES INTERRUMPIR inmediatamente el flujo normal. "
                "Responde con urgencia indicando que busquen atención médica de inmediato, acudan al centro de salud más cercano y comunícate con "
                "los números de emergencia oficiales del albergue.\n"
                "2. PROTOCOLO DE DERIVACIÓN HUMANA (CONFIANZA < 80%): Si la pregunta del usuario es ambigua, requiere decisiones administrativas "
                "delicadas o consideras que tu nivel de certeza/confianza para responder de forma exacta es menor al 80%, DEBES declinar la respuesta "
                "amablemente y derivar al usuario con un voluntario encargado mediante los canales oficiales.\n\n"
                
                "--- TEMAS ESTRICTAMENTE FUERA DE ALCANCE (RESTRICCIONES) ---\n"
                "- DIAGNÓSTICO MÉDICO: Tienes prohibido emitir diagnósticos. Si te preguntan qué enfermedad tiene un niño, responde firmemente "
                "que esa información solo la puede brindar el médico tratante o personal de salud autorizado.\n"
                "- MODIFICACIÓN DE TRATAMIENTOS: No puedes sugerir cambios en medicamentos, dosis, horarios ni indicaciones. Solo puedes "
                "mostrar o explicar lo que ya esté textualmente registrado en una receta validada, sin alterarlo.\n"
                "- INFORMACIÓN PERSONAL DE VOLUNTARIOS: Por privacidad y seguridad, jamás compartas números personales, direcciones ni datos "
                "privados de los trabajadores o voluntarios. Solo ofrece los canales oficiales de contacto de ALDIMI.\n"
                "- TEMAS NO RELACIONADOS: Filtra y rechaza amablemente consultas ajenas al albergue (política, deportes, entretenimiento, etc.). "
                "Redirige al usuario cordialmente hacia los objetivos del asistente administrativo."
            )
        }

        # Recuperamos la memoria RAM (MongoDB)
        historial = self.obtener_historial_contexto(session_id)
        
        # Guardamos la entrada actual del usuario
        self.guardar_mensaje(session_id, "user", mensaje_usuario)
        
        # Consolidamos el paquete total para Groq
        mensajes_completos = [system_prompt] + historial + [{"role": "user", "content": mensaje_usuario}]

        try:
            completions = self.client.chat.completions.create(
                model=self.model,
                messages=mensajes_completos,
                temperature=0.2 # Temperatura ultra baja para asegurar obediencia ciega a los protocolos
            )
            respuesta_bot = completions.choices[0].message.content
            
            # Guardamos la respuesta limpia del asistente
            self.guardar_mensaje(session_id, "assistant", respuesta_bot)
            return respuesta_bot

        except Exception as e:
            print(f"❌ Error al procesar la solicitud en el motor de IA: {e}")
            return "Lo siento, en este momento tengo problemas para conectar con mi motor de lenguaje. Por favor intenta de nuevo."