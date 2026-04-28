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
import os
import re

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

        # Handle both absolute and relative paths
        if not os.path.isabs(image_path):
            from django.conf import settings
            image_path = os.path.join(settings.MEDIA_ROOT, image_path)
        
        logger.info(f"Encoding image: {image_path}")
        
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


def _normalize(vec):
    norm = np.linalg.norm(vec)
    if norm == 0 or not np.isfinite(norm):
        return None
    return vec / norm


def _tokenize(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def search_photos(
    query,
    photos_with_embeddings,
    top_k=20,
    min_score=0.28,
    min_semantic_score=0.22,
    fallback_min_score=0.18,
    fallback_min_semantic_score=0.12,
):
    if not photos_with_embeddings:
        return []

    # CLIP is usually stronger with natural prompts than single tokens.
    query_prompts = [
        query,
        f"a photo of {query}",
        f"an image of {query}",
    ]
    text_vectors = []
    for prompt in query_prompts:
        try:
            text_embedding = encode_text(prompt)
            text_vec = np.array(text_embedding, dtype=np.float32)
            text_vec = _normalize(text_vec)
            if text_vec is not None:
                text_vectors.append(text_vec)
        except Exception:
            continue

    if not text_vectors:
        logger.warning("Search query produced no valid text embeddings.")
        return []

    text_vec = _normalize(np.mean(text_vectors, axis=0))
    if text_vec is None:
        return []

    query_tokens = _tokenize(query)

    scored_items = []

    for item in photos_with_embeddings:
        try:
            img_vec = np.array(item.get('embedding'), dtype=np.float32)
        except Exception:
            continue

        if img_vec.size == 0 or img_vec.shape != text_vec.shape:
            continue

        img_vec = _normalize(img_vec)
        if img_vec is None:
            continue

        semantic_score = float(np.dot(text_vec, img_vec))
        score = semantic_score

        # Small keyword boost from title/filename to improve precision for simple terms like "dog".
        title_tokens = _tokenize(item.get('title', ''))
        if query_tokens and title_tokens:
            overlap = len(query_tokens.intersection(title_tokens))
            token_boost = min(0.1, overlap * 0.05)
            score += token_boost

        if not np.isfinite(score):
            continue

        scored_items.append({
            'id': item['id'],
            'score': score,
            'semantic_score': semantic_score
        })

    if not scored_items:
        return []

    scored_items.sort(key=lambda x: x['score'], reverse=True)

    def _filter(items, score_cutoff, semantic_cutoff):
        return [
            i for i in items
            if i['semantic_score'] >= semantic_cutoff and i['score'] >= score_cutoff
        ]

    # First pass: strict confidence filtering.
    strict_results = _filter(scored_items, min_score, min_semantic_score)
    if strict_results:
        return strict_results[:top_k]

    # Fallback pass: if strict mode returns nothing, relax thresholds to avoid empty UX.
    relaxed_results = _filter(
        scored_items,
        fallback_min_score,
        fallback_min_semantic_score
    )
    if relaxed_results:
        return relaxed_results[:top_k]

    # Last-resort fallback: return top positive-semantic matches so users still get results.
    positive_semantic = [i for i in scored_items if i['semantic_score'] > 0.05]
    if positive_semantic:
        return positive_semantic[: min(top_k, 10)]

    # Absolute fallback: return best available ranked items.
    return scored_items[: min(top_k, 5)]