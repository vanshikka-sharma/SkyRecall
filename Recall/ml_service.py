"""
CLIP-based semantic search service for SkyRecall.
Uses OpenAI's CLIP model to encode images and text into the same embedding space,
enabling natural language image search.
"""

import torch
import numpy as np
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import logging

logger = logging.getLogger(__name__)

# Global model instance (loaded once)
_model = None
_processor = None
_device = None


def get_model():
    """Lazy-load CLIP model (only once per server lifetime)."""
    global _model, _processor, _device

    if _model is None:
        logger.info("Loading CLIP model... (first time only, may take ~30 seconds)")
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        _model = _model.to(_device)
        _model.eval()
        logger.info(f"CLIP model loaded on {_device}")

    return _model, _processor, _device


def encode_image(image_path: str) -> list:
    """
    Encode an image file into a CLIP embedding vector.
    Returns a list of floats (512-dim vector).
    """
    try:
        model, processor, device = get_model()

        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt").to(device)

        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
            # Normalize the embedding
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        return image_features.cpu().numpy()[0].tolist()

    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {e}")
        raise


def encode_text(text: str) -> list:
    """
    Encode a text query into a CLIP embedding vector.
    Returns a list of floats (512-dim vector).
    """
    try:
        model, processor, device = get_model()

        inputs = processor(text=[text], return_tensors="pt", padding=True).to(device)

        with torch.no_grad():
            text_features = model.get_text_features(**inputs)
            # Normalize the embedding
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        return text_features.cpu().numpy()[0].tolist()

    except Exception as e:
        logger.error(f"Error encoding text '{text}': {e}")
        raise


def cosine_similarity(vec1: list, vec2: list) -> float:
    """Compute cosine similarity between two embedding vectors."""
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search_photos(query, photos_with_embeddings, top_k=20):
    if not photos_with_embeddings:
        return []

    text_embedding = encode_text(query)
    text_vec = np.array(text_embedding)

    results = []

    for item in photos_with_embeddings:
        img_vec = np.array(item['embedding'])
        score = float(np.dot(text_vec, img_vec))

        results.append({
            'id': item['id'],
            'score': score
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]