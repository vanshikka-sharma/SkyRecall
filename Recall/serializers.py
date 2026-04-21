from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Photo


# class RegisterSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, min_length=6)
#     password2 = serializers.CharField(write_only=True)

#     class Meta:
#         model = User
#         fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2']

#     def validate_username(self, value):
#         if User.objects.filter(username=value).exists():
#             raise serializers.ValidationError("Username already exists.")
#         return value

#     def validate(self, data):
#         if data['password'] != data['password2']:
#             raise serializers.ValidationError({"password": "Passwords do not match."})
#         return data

#     def create(self, validated_data):
#         validated_data.pop('password2')
#         user = User.objects.create_user(**validated_data)
#         return user

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],  # THIS hashes password automatically
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class PhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    has_embedding = serializers.SerializerMethodField()

    class Meta:
        model = Photo
        fields = ['id', 'title', 'image_url', 'uploaded_at', 'has_embedding']
        read_only_fields = ['uploaded_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_has_embedding(self, obj):
        return bool(obj.embedding)


class PhotoUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ['id', 'image', 'title']

    def create(self, validated_data):
        user = self.context['request'].user
        photo = Photo.objects.create(user=user, **validated_data)
        return photo