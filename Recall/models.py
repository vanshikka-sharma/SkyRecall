from django.db import models
from django.utils import timezone
# Create your models here.
from django.db import models
from django.contrib.auth.models import User
import json


class Photo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='photos/%Y/%m/%d/')
    title = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # Store CLIP embedding as JSON (list of floats)
    embedding = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.user.username} - {self.title or self.image.name}"

    def get_embedding(self):
        if self.embedding:
            return json.loads(self.embedding)
        return None

    def set_embedding(self, embedding_list):
        self.embedding = json.dumps(embedding_list)