import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkyRecall.settings')
django.setup()

from Recall import ml_service
from Recall.models import Photo
import traceback

try:
    user_photos = Photo.objects.filter(embedding__isnull=False).exclude(embedding='')
    photos_data = [{'id': p.id, 'embedding': p.get_embedding()} for p in user_photos]
    print(f"Loaded {len(photos_data)} photos")
    res = ml_service.search_photos('test query', photos_data)
    print("Search successful!")
    print(res)
except Exception as e:
    print("Search failed:")
    traceback.print_exc()
