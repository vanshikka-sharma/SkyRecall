from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image

# Load once
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")


def get_image_embedding(image_path):
    image = Image.open(image_path)
    inputs = processor(images=image, return_tensors="pt")
    outputs = model.get_image_features(**inputs)
    return outputs.detach().numpy()[0]


def get_text_embedding(text):
    inputs = processor(text=[text], return_tensors="pt")
    outputs = model.get_text_features(**inputs)
    return outputs.detach().numpy()[0]