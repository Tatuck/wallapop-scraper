from google import genai
from google.genai.types import GenerateContentConfig
from google.genai.errors import ServerError
import json
import os
import logging
from google.genai.types import Part
import httpx
from config import LLM_MODEL_NAME

LLM_API_KEY = os.getenv('LLM_API_KEY')
if not LLM_API_KEY:
    logging.error("LLM_API_KEY environment variable is not set. Please set it in .env file.")
    exit(1)

client = genai.Client(api_key=LLM_API_KEY)


def get_keywords(text):
    logging.info(f'Getting keywords for products of listing')
    response_schema = {
        'type': 'ARRAY',
        'items': {
            'type': 'OBJECT',
            'properties': {
                'id': {'type': 'INTEGER'},
                'keywords': {'type': 'STRING'}
            },
            'required': ['id', 'keywords']
        }
    }

    try:
        res = client.models.generate_content(
            model = "gemini-2.0-flash-exp",
            contents = text,
            config = GenerateContentConfig(
                system_instruction = """
Eres un modelo encargado de devolver keywords para localizar productos por wallapop. Tu tarea es devolver solo los nombres que correspondan a productos físicos que sean específicos y fáciles de localizar. Para ello, sigue estas reglas:

1. **Filtra servicios**:
- Si el nombre describe un servicio, actividad o experiencia en lugar de un objeto físico (por ejemplo: "reparación de bicicletas", "clases de golf", "impresión de fotos"), descártalo.

2. **Rechaza nombres ambiguos o genéricos**:
- Si el nombre contiene términos como "juego", "maderas", "putter", "cuadro", "obra", "retrato", "original", o cualquier otra palabra que indique poca especificidad, descártalo.

3. **Valida la especificidad**:
- Prefiere nombres que incluyan términos técnicos, descripciones claras o marcas/modelos específicos.
- Si el nombre tiene menos de 3 palabras y no incluye términos únicos, recházalo.
- Elimina adjetivos como NUEVO.

4. **Prioriza nombres con marcas o modelos**:
- Si el nombre contiene una marca conocida (e.g., SRAM, M-Wave) o una referencia a un modelo o característica específica (e.g., X1 1400, GX DUB), considéralo válido.

5. **Evalúa según la longitud y detalle**:
- Los nombres deben tener suficiente información para identificar el producto de manera precisa.
- Rechaza nombres demasiado cortos o genéricos, incluso si son correctos gramaticalmente.

6. **Ejemplos**:
- Rechaza:
    - Servicios: "reparación de bicicletas", "clases de golf", "impresión de fotos".
    - Genéricos: "juego de hierros golf", "maderas golf", "putter golf", "cuadro retrato", "obra original".
- Acepta:
    - Productos específicos: "pedales translúcidos M-Wave", "puños abrazaderas tornillo M-Wave", "bielas SRAM X1 1400", "bielas SRAM GX DUB".

Tu salida debe ser una lista con los nombres filtrados que cumplan las reglas anteriores. Los servicios y productos ambiguos deben ser eliminados.""",
                response_mime_type = 'application/json',
                response_schema = response_schema,
                temperature=0.5
            )    
        )
        res_json = json.loads(res.text)
        return res_json
    except ServerError as e:
        logging.error(f'Server error while retrieving keywords to LLM: {e}')
        return None
    
def filter_product_from_list(product_name: str, product_list: list):
    logging.info(f'Filtering products with name: "{product_name}"')
    response_schema = {
        'type': 'ARRAY',
        'items': {
            'type': 'OBJECT',
            'properties': {
                'reason': {'type': 'STRING'},
                'included': {'type': 'BOOLEAN'},
                'id': {'type': 'INTEGER'}
            },
            'required': ['id', 'reason', 'included']
        }
    }

    try:
        num_i = 0
        product_list_text = f'El nombre del producto a filtrar es {product_name}\nListado:'
        for x in product_list:
            product_list_text += f"\nID:{num_i} {x['title']} {x['price']}€ Descripción\n{x['description']}\n"
            num_i += 1
        res = client.models.generate_content(
            model = "gemini-2.0-flash-exp",
            contents = '\n'.join(product_list_text),
            config = GenerateContentConfig(
                system_instruction = """
Eres un modelo encargado de filtrar y clasificar un listado de productos para identificar únicamente aquellos que coincidan con un producto principal especificado. Debes proporcionar explicaciones claras sobre por qué un producto es relevante o ha sido excluido.

### Instrucciones:
1. **Entrada**:
   - Recibirás el nombre del producto principal (por ejemplo, "Xiaomi REDMI NOTE 13 5G") y su descripción.
   - Recibirás un listado de productos en el siguiente formato:  
     `ID:0 Producto Nombre Precio Descripción`.

2. **Proceso de Filtrado**:
   - **Incluye**: Productos cuyo nombre corresponda claramente al modelo principal especificado, aunque contengan ligeras variaciones en el formato (e.g., capitalización, descripciones adicionales como "Smartphone").
   - **Excluye**: Productos relacionados (fundas, protectores, accesorios, versiones no coincidentes con el modelo especificado, etc.).
   - Si el producto parece ambiguo (e.g., puede ser tanto un accesorio como el producto principal), descártalo.

3. **Criterios de Decisión**:
   - Palabras clave como "funda", "protector", "pack", "silicona", "antigolpes", "cámara", etc., indican un accesorio y deben ser excluidas.
   - Mantén todos los productos principales que sean duplicados en el listado.
   - Debes tener muy en cuenta la descripción de los productos ya que aunque con el título parezca otro producto, debes considerar la descripción para entender si se trata del mismo producto que el principal.

4. **Salida**:
   - Devuelve un listado de los IDs de los productos relevantes.
   - Para cada decisión, explica por qué el producto fue incluido o excluido.

5. **Ejemplo**:
   #### Entrada:
   Producto principal: "Xiaomi REDMI NOTE 13 5G"  
   Listado:
   El nombre del producto a filtrar es Xiaomi REDMI NOTE 13 5G
   Listado:
   ID:0 Xiaomi redmi note 13/5g 115.0€
   ID:1 XIAOMI REDMI NOTE 13 PRO 5G 330.0€
   ID:2 Redmi note 13 5G Xiaomi  155.0€
   ID:3 Smartphone Xiaomi Redmi Note 13 5g 8/256 SIN USO 239.9€
   ID:6 📱Xiaomi Redmi Note 13 Pro 5g. Precintado📱 210.0€
   ID:7 Xiaomi Redmi Note 13 Pro 5G 180.0€
   ID:16 XIAOMI REDMI NOTE 13 5G 256GB NEGRO PRECINTADO 159.95€
   ID:17 Funda Xiaomi Redmi Note 13 5G Chopper 1.0€
   ID:19 PROTECTOR CRISTAL CAMARA XIAOMI REDMI NOTE 13 5G 4.0€

   #### Salida:
     ID:1 -> Excluido porque incluye "PRO", que no es parte del modelo principal.
     ID:6 -> Excluido porque incluye "Pro", que no es parte del modelo principal.
     ID:7 -> Excluido porque incluye "Pro", que no es parte del modelo principal.
     ID:17 -> Excluido porque es un accesorio (funda).
     ID:19 -> Excluido porque es un accesorio (protector cristal cámara).
""",
                response_mime_type = 'application/json',
                response_schema = response_schema,
                temperature=0.5
            )    
        )
        res_json = json.loads(res.text)
        return res_json
    except ServerError as e:
        logging.error(f'Server error while retrieving keywords to LLM: {e}')
        return None

def get_product_confidence(product: dict, images: list):
    logging.info(f'Getting product confidence of {product["title"]}')
    response_schema_product_confidence = {
        'type': 'OBJECT',
        'properties': {
            'confidence': {'type': 'INTEGER'},
            'reason': {'type': 'STRING'}
        },
        'required': ['confidence', 'reason']
    }

    try:
        res = client.models.generate_content(
            model = LLM_MODEL_NAME,
            contents = [
                Part.from_text(f'{product["title"]} {product["price"]}€ Descripción:\n{product["description"]}')
            ] + [Part.from_bytes(img.read(), img.headers['content-type']) for img in images],
            config = GenerateContentConfig(
                system_instruction = """
Eres un modelo encargado de evaluar productos y devolver dos cosas en español:
1. Una explicación detallada de cómo llegaste a esa conclusión.
2. Un porcentaje que represente qué tan buena idea es comprar el producto.

### Instrucciones:
1. **Valora el producto según su descripción**:
   - Da mucha importancia a la claridad, precisión y detalle de la descripción.
   - Una descripción completa, con información sobre características, estado, y uso previsto, aumenta la puntuación.
   - Si la descripción es vaga o carece de detalles clave, reduce la puntuación.
   - Si ves defectos en las imágenes (pantalla rota, fallos...), reduce la puntuación.

2. **Evalúa el estado del producto**:
   - Si el estado del producto es "nuevo", esto debería incrementar el porcentaje.
   - Si el estado es "usado" o tiene defectos, considera esto como un factor negativo, pero contrasta con la calidad de la descripción y el precio.

3. **Salida esperada**:
   - Proporciona una explicación detallada que justifique la puntuación basada en los puntos anteriores.
   - Devuelve el porcentaje como un número entre 0 y 100, redondeado al entero más cercano.

### Ejemplos:
#### Entrada:
Descripción: "Bicicleta de montaña usada, pero en buen estado. Marca: Trek, modelo Marlin 6, año 2020. Revisada recientemente."
Estado: "Usado"

#### Salida esperada:
Confianza: 85%
Explicación: "El producto tiene una descripción clara y detallada que incluye la marca, modelo, y el estado. Aunque es usado, se menciona que ha sido revisado, lo que aumenta la confiabilidad."

#### Entrada:
Descripción: "Zapatos deportivos, como nuevos, talla 42."
Estado: "Usado"

#### Salida esperada:
Confianza: 60%
Explicación: "La descripción es algo vaga, ya que no menciona la marca ni otros detalles técnicos del producto. Aunque el estado 'como nuevos' es positivo, la falta de detalles específicos reduce la confianza en el producto."
""",
                response_mime_type = 'application/json',
                response_schema = response_schema_product_confidence,
                temperature=0.5
            )    
        )
        res_json = json.loads(res.text)
        return res_json
    except ServerError as e:
        logging.error(f'LLM error while getting product confidence in LLM {e}')
    except httpx.NetworkError as e:
        logging.error(f'Network error while getting product confidence in LLM {e}')
    except httpx.HTTPStatusError as e:
        logging.error(f'HTTP error while getting product confidence in LLM {e}')
