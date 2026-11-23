import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import base64
from typing import Optional
from groq import Groq
import config

vision_model = config.VISION_MODEL
_vision_client: Optional[Groq] = None


def get_vision_client() -> Groq:
    """Lazily initializes and returns the Groq client."""
    global _vision_client
    if _vision_client is None:
        if not config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set. Please add it to your .env file.")
        _vision_client = Groq(api_key=config.GROQ_API_KEY)
    return _vision_client


def ask_vision_model(
    client: Optional[Groq],
    model: str,
    image_bytes: bytes,
    prompt: str = "Describe this image, diagram, or chart in detail. Extract all visible text, numbers, and key relationships."
) -> str:
    """Takes image bytes and returns a detailed textual description using Groq Vision."""
    client = client or get_vision_client()
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64_image}"}
                    }
                ]
            }
        ],
        max_tokens=300
    )
    return response.choices[0].message.content
