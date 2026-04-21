from django.contrib import admin
from .models import Photo
 
@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'uploaded_at', 'has_embedding']
    list_filter = ['user', 'uploaded_at']
    search_fields = ['title', 'user__username']
 
    def has_embedding(self, obj):
        return bool(obj.embedding)
    has_embedding.boolean = True
