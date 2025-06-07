from fastapi import FastAPI, File, UploadFile, Query
from fastapi.responses import JSONResponse
import torch
from torchvision import transforms, models
import torch.nn as nn
from PIL import Image
import io
import requests
from typing import Optional, Dict, List
import uvicorn
from transformers import AutoImageProcessor, AutoModelForImageClassification
import logging
import timm
from ultralytics import YOLO
import open_clip

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Model Object Detector Service")

class ModelManager:
    def __init__(self):
        self.models: Dict[str, nn.Module] = {}
        self.processors: Dict[str, any] = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        try:
            self.models['clip'], _, self.processors['clip'] = open_clip.create_model_and_transforms(
                "ViT-B-32", pretrained="laion2b_s34b_b79k"
            )
            self.models['clip'].to(self.device).eval()
            logger.info("Модель CLIP успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели CLIP: {str(e)}")
            raise

    def get_predictions(self, image: Image.Image, model_name: str, object_name: str) -> List[dict]:
        try:
            if model_name == 'clip':
                image_tensor = self.processors[model_name](image).unsqueeze(0).to(self.device)
                
                prompt = f"a photo of a {object_name}"
                
                with torch.no_grad():
                    image_features = self.models[model_name].encode_image(image_tensor)
                    image_features /= image_features.norm(dim=-1, keepdim=True)
                
                text_tokens = open_clip.tokenize([prompt]).to(self.device)
                
                with torch.no_grad():
                    text_features = self.models[model_name].encode_text(text_tokens)
                    text_features /= text_features.norm(dim=-1, keepdim=True)
                
                similarity = (image_features @ text_features.T).squeeze(0)
                probability = similarity.item()
                
                return [{
                    "category": object_name,
                    "probability": probability,
                    "best_prompt": prompt
                }]

        except Exception as e:
            logger.error(f"Ошибка при получении предсказаний от модели {model_name}: {str(e)}")
            return []

model_manager = ModelManager()

@app.post("/detect_object")
async def detect_object(
    file: UploadFile = File(...),
    object_name: str = Query(..., description="Название объекта для поиска на изображении")
):
    try:
        contents = await file.read()
        if not contents:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Получен пустой файл"}
            )

        try:
            image = Image.open(io.BytesIO(contents))
            logger.info(f"Изображение успешно загружено. Размер: {image.size}")
        except Exception as e:
            logger.error(f"Ошибка при открытии изображения: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Не удалось открыть изображение: {str(e)}"}
            )

        if image.size != (130, 130):
            logger.info(f"Изменение размера изображения с {image.size} на (130, 130)")
            image = image.resize((130, 130), Image.Resampling.LANCZOS)

        results = model_manager.get_predictions(image, 'clip', object_name)
        
        object_found = results[0]["probability"] > 0.3 if results else False

        return JSONResponse(content={
            "success": True,
            "results": {
                "clip": results,
                "clip_found": object_found
            },
            "image_size": image.size
        })

    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Неожиданная ошибка: {str(e)}"}
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008) 