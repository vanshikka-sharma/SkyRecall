from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Photo
from .serializers import (
    RegisterSerializer, UserSerializer,
    PhotoSerializer, PhotoUploadSerializer
)
from . import ml_service
import logging
import os

logger = logging.getLogger(__name__)


# ─── AUTH VIEWS ────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]    #AllowAny

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Account created successfully!',
                'user': UserSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {'error': 'Invalid credentials. Please try again.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'message': f'Welcome back, {user.first_name or user.username}!',
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return Response({'message': 'Logged out successfully.'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ─── PHOTO VIEWS ───────────────────────────────────────────────────────────────

class PhotoListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        photos = Photo.objects.filter(user=request.user).order_by('-uploaded_at')
        serializer = PhotoSerializer(photos, many=True, context={'request': request})
        return Response({
            'count': photos.count(),
            'photos': serializer.data
        })


class PhotoUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("USER:", request.user)
        print("AUTH:", request.auth)
        images = request.FILES.getlist('images')

        if not images:
            return Response(
                {'error': 'No images provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(images) > 50:
            return Response(
                {'error': 'Maximum 50 images per upload.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded = []
        errors = []
    
        for image_file in images:
            try:
                # Validate file type
                if not image_file.content_type.startswith('image/'):
                    errors.append(f"{image_file.name}: Not an image file.")
                    continue

                # Create photo record
                photo = Photo.objects.create(
                    user=request.user,
                    image=image_file,
                    title=os.path.splitext(image_file.name)[0]
                )

                # Generate CLIP embedding
                try:
                    image_path = photo.image.path
                    logger.info(f"Generating embedding for: {image_path}")
                    
                    # ONLY run if ML is working
                    embedding = ml_service.encode_image(image_path)
                    photo.set_embedding(embedding)
                    photo.save()
                    logger.info(f"Embedding generated for photo {photo.id}")

                except Exception as e:
                    logger.error(f"Embedding failed (IGNORED): {e}")
                   # IMPORTANT: DO NOT break upload
                    pass
                    # Photo saved but without embedding - search won't work for it

                uploaded.append(PhotoSerializer(photo, context={'request': request}).data)

            except Exception as e:
                errors.append(f"{image_file.name}: {str(e)}")

        return Response({
            'uploaded': uploaded,
            'count': len(uploaded),
            'errors': errors,
            'message': f'{len(uploaded)} photo(s) uploaded successfully!'
        }, status=status.HTTP_201_CREATED)


class PhotoDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            photo = Photo.objects.get(pk=pk, user=request.user)
        except Photo.DoesNotExist:
            return Response({'error': 'Photo not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Delete the actual image file
        if photo.image:
            try:
                os.remove(photo.image.path)
            except Exception:
                pass

        photo.delete()
        return Response({'message': 'Photo deleted.'}, status=status.HTTP_204_NO_CONTENT)


class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()

        if not query:
            return Response({'error': 'Search query is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(query) < 2:
            return Response({'error': 'Query too short.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get all photos for user that have embeddings
        user_photos = Photo.objects.filter(user=request.user, embedding__isnull=False).exclude(embedding='')

        if not user_photos.exists():
            return Response({
                'query': query,
                'results': [],
                'count': 0,
                'message': 'No photos with embeddings found. Please upload photos first.'
            })

        # Prepare data for search
        photos_data = []
        for photo in user_photos:
            try:
                embedding = photo.get_embedding()
            except Exception:
                logger.warning("Skipping photo %s due to invalid embedding JSON.", photo.id)
                continue

            if not embedding:
                continue

            photos_data.append({
                'id': photo.id,
                'embedding': embedding,
                'title': photo.title or ''
            })

        if not photos_data:
            return Response({
                'query': query,
                'results': [],
                'count': 0,
                'message': 'No valid indexed photos found. Please re-upload affected photos.'
            })

        # Run semantic search
        try:
            search_results = ml_service.search_photos(query, photos_data)
        except Exception as e:
            logger.exception("Search failed for query '%s'", query)
            error_payload = {'error': 'Search engine error. Please try again.'}
            if settings.DEBUG:
                error_payload['details'] = str(e)
            return Response(error_payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Fetch matched photos in order
        result_ids = [r['id'] for r in search_results]
        score_map = {r['id']: r['score'] for r in search_results}

        photos_map = {p.id: p for p in user_photos.filter(id__in=result_ids)}

        results = []
        for photo_id in result_ids:
            if photo_id in photos_map:
                photo = photos_map[photo_id]
                data = PhotoSerializer(photo, context={'request': request}).data
                data['score'] = round(score_map[photo_id], 4)
                results.append(data)

        return Response({
            'query': query,
            'results': results,
            'count': len(results),
        })


class StatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total = Photo.objects.filter(user=request.user).count()
        indexed = Photo.objects.filter(
            user=request.user,
            embedding__isnull=False
        ).exclude(embedding='').count()

        return Response({
            'total_photos': total,
            'indexed_photos': indexed,
            'pending_indexing': total - indexed,
        })
