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

    def responder_con_contexto(self, session_id: str, mensaje_usuario: str, usuario_tipo: str) -> str:
        """
        Responde las consultas aplicando restricciones estrictas según el rol del usuario
        Roles válidos: 'Voluntario', 'Padres de Familia', 'Administrador', 'Personal de apoyo'
        """
        cantidad_pacientes = self.obtener_total_pacientes_real()

        # 1. Definimos las directrices específicas por cada Rol (Gestión de Usuarios)
        directrices_roles = {
            "Voluntario": (
                "El usuario actual es un VOLUNTARIO. Tienes permitido asistirlo exclusivamente en: "
                "Consultar protocolos internos, normas del albergue y pasos de atención al paciente. "
                "Sé un soporte operativo eficiente para ellos."
            ),
            "Padres de Familia": (
                "El usuario actual es un PADRE DE FAMILIA. Tienes permitido asistirlo exclusivamente en: "
                "Recibir orientación sobre las reglas de convivencia del albergue, cuidados generales "
                "del niño en las instalaciones y pautas de adaptación. Usa un tono sumamente empático, "
                "cálido y contenedor. Jamás reveles datos administrativos internos."
            ),
            "Administrador": (
                "El usuario actual es el ADMINISTRADOR del sistema. Tienes acceso total. "
                "Puedes ayudarlo a revisar alertas del sistema, verificar el estado de los documentos "
                "procesados por el OCR y analizar la trazabilidad de los registros médicos y donaciones."
            ),
            "Personal de apoyo": (
                "El usuario actual es PERSONAL DE APOYO. Tienes permitido asistirlo exclusivamente en: "
                "Consultar información operativa diaria del albergue, horarios, logística interna y "
                "tareas de mantenimiento o soporte asignadas."
            )
        }

        # Validamos que el rol exista, si no, le asignamos restricciones básicas por seguridad
        instruccion_rol = directrices_roles.get(
            usuario_tipo, 
            "Usuario no identificado. Por seguridad, restringe cualquier información sensible."
        )

        # 2. Construimos el System Prompt Dinámico combinando Contexto, Roles y Reglas de Negocio
        system_prompt = {
            "role": "system",
            "content": (
                "Eres ALDIMI-Assist, el asistente oficial de Inteligencia Artificial del Albergue Divina Misericordia (ALDIMI).\n"
                "Tu objetivo es ayudar con empatía, profesionalismo y brevedad. Responde siempre en español.\n\n"
                
                f"--- PERMISOS DE SEGURIDAD (GESTIÓN DE USUARIOS) ---\n"
                f"{instruccion_rol}\n"
                "CRÍTICO: Si el usuario intenta solicitar acciones o información que no corresponden a su rol asignado, "
                "debes denegar la respuesta amablemente y recordarle cuáles son sus opciones disponibles.\n\n"
                
                f"--- CONTEXTO EN VIVO (TABLAS RELACIONALES) ---\n"
                f"Actualmente el albergue tiene exactamente {cantidad_pacientes} paciente(s) registrado(s) en la tabla dni_master.\n\n"
                
                "--- PROTOCOLOS PRIORITARIOS DE ACTUACIÓN ---\n"
                "1. PROTOCOLO DE EMERGENCIA MÉDICA: Si el usuario menciona 'fiebre alta', 'convulsión', 'dificultad para respirar' o emergencias, "
                "interrumpe el flujo normal, indica buscar atención médica urgente, ve al centro de salud más cercano y llama a los números del albergue.\n"
                "2. PROTOCOLO DE DERIVACIÓN HUMANA (CONFIANZA < 80%): Si la certeza de tu respuesta es menor al 80% o requiere decisiones "
                "humanas delicadas, declina amablemente y deriva con un voluntario encargado por canales oficiales.\n\n"
                
                "--- TEMAS ESTRICTAMENTE FUERA DE ALCANCE (REGLAS DE NEGOCIO) ---\n"
                "- DIAGNÓSTICO MÉDICO: Prohibido diagnosticar. Remite siempre al médico tratante.\n"
                "- MODIFICACIÓN DE TRATAMIENTOS: No alteres dosis, medicamentos ni horarios de recetas. Solo explica lo registrado.\n"
                "- INFORMACIÓN PERSONAL: Jamás compartas datos privados o teléfonos de trabajadores/voluntarios. Solo canales oficiales.\n"
                "- TEMAS NO RELACIONADOS: Filtra política, deportes o entretenimiento. Mantén el foco en ALDIMI."
            )
        }

        # 3. Recuperamos la memoria RAM de la sesión (MongoDB)
        historial = self.obtener_historial_contexto(session_id)
        
        # Guardamos la entrada del usuario
        self.guardar_mensaje(session_id, "user", mensaje_usuario)
        
        # Consolidamos los mensajes para Groq
        mensajes_completos = [system_prompt] + historial + [{"role": "user", "content": mensaje_usuario}]

        try:
            completions = self.client.chat.completions.create(
                model=self.model,
                messages=mensajes_completos,
                temperature=0.2
            )
            respuesta_bot = completions.choices[0].message.content
            
            # Guardamos la respuesta del asistente en MongoDB
            self.guardar_mensaje(session_id, "assistant", respuesta_bot)
            return respuesta_bot

        except Exception as e:
            print(f"❌ Error al procesar la solicitud en el motor de IA: {e}")
            return "Lo siento, en este momento tengo problemas para conectar con mi motor de lenguaje. Por favor intenta de nuevo."
        
    def obtener_historial_contexto(self, session_id: str):
            """
            Recupera el historial de chat de MongoDB usando history_collection
            """
            if self.history_collection is None:
                return []
            try:
                # 💡 Cambiado de self.chat_logs a self.history_collection
                logs = self.history_collection.find({"session_id": session_id}).sort("timestamp", 1)
                
                historial = []
                for log in logs:
                    historial.append({
                        "role": log.get("role"),
                        "content": log.get("content")
                    })
                return historial
            except Exception as e:
                print(f"⚠️ Error al recuperar historial de MongoDB: {e}")
                return []

    def guardar_mensaje(self, session_id: str, role: str, content: str):
        """
        Guarda un nuevo mensaje en MongoDB usando history_collection
        """
        if self.history_collection is None:
            return
        from datetime import datetime, timezone
        try:
            # 💡 Cambiado de self.chat_logs a self.history_collection
            self.history_collection.insert_one({
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc)
            })
        except Exception as e:
            print(f"⚠️ Error al guardar mensaje en MongoDB: {e}")