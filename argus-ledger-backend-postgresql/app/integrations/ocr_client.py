import base64
import os


class OCRClient:
    # Priority: teammate OCR -> optional Google Vision -> unavailable.

    async def analyze(self, image_bytes, filename="image"):
        from .config import config
        if config.ai_engine_url:
            from .ai_engine_client import AIEngineClient
            return await AIEngineClient().ocr({
                "filename": filename,
                "image_base64": base64.b64encode(image_bytes).decode("ascii"),
            })

        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            return self._google_vision(image_bytes)

        return {"enabled": False, "text": "", "reason": "No OCR provider configured"}

    @staticmethod
    def _google_vision(image_bytes):
        try:
            from google.cloud import vision
        except ImportError:
            return {
                "enabled": False,
                "text": "",
                "reason": "GOOGLE_APPLICATION_CREDENTIALS is set but "
                          "google-cloud-vision is not installed",
            }
        client = vision.ImageAnnotatorClient()
        response = client.text_detection(image=vision.Image(content=image_bytes))
        if response.error.message:
            raise RuntimeError(response.error.message)
        text = response.text_annotations[0].description if response.text_annotations else ""
        return {"enabled": True, "provider": "google-cloud-vision", "text": text}
