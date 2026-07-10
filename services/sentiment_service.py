import os
import json
from openai import OpenAI

class SentimentService:
    def __init__(self):
        # Inicializamos el cliente de OpenAI apuntando a la infraestructura de Groq
        self.client = OpenAI(
            base_url=os.getenv("OPENAI_API_BASE"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.model = os.getenv("NLP_MODEL_NAME", "llama-3.1-8b-instant")

    def analizar_reporte(self, texto_reporte: str) -> dict:
        """
        Analiza el texto de un reporte de evolución utilizando Groq en modo JSON.
        Retorna un diccionario con el sentimiento predicho y el nivel de criticidad.
        """
        # Definimos las reglas estrictas de análisis para el modelo de lenguaje
        system_prompt = (
            "Eres un experto en análisis de texto clínico y psicológico para el Albergue Divina Misericordia. "
            "Tu tarea es evaluar el reporte de evolución de un paciente infantil con cáncer y determinar dos métricas:\n"
            "1. 'sentimiento': Debe ser estrictamente uno de estos tres valores: 'Positivo', 'Neutral' o 'Negativo'.\n"
            "2. 'criticidad': Un número entero del 1 al 5, donde 1 es estabilidad total y 5 es una alerta médica/emocional crítica.\n\n"
            "DEBES responder ÚNICA Y EXCLUSIVAMENTE con un objeto JSON válido con la siguiente estructura:\n"
            "{\n"
            "  \"sentimiento\": \"valor\",\n"
            "  \"criticidad\": número\n"
            "}"
        )

        try:
            # Forzamos a Groq a utilizar su "JSON Mode" para garantizar estabilidad en la respuesta
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analiza el siguiente reporte:\n\n{texto_reporte}"}
                ],
                temperature=0.1, # Temperatura baja para que sea determinista y altamente preciso
                response_format={"type": "json_object"} # Característica nativa de Groq/OpenAI
            )

            # Extraemos el contenido de la respuesta (que viene como String tipo JSON)
            raw_json = response.choices[0].message.content
            
            # Lo transformamos a un diccionario nativo de Python
            resultado_parseado = json.loads(raw_json)
            return resultado_parseado

        except Exception as e:
            print(f"❌ Error en SentimentService: {e}")
            # Retornamos un valor por defecto seguro en caso de que la API de Groq falle
            return {
                "sentimiento": "Neutral",
                "criticidad": 3
            }