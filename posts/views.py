from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from .models import NeedPost, OfferPost, Tag, Image
from .serializers import (
    NeedPostSerializer,
    OfferPostSerializer,
    UserAndBusinessPostListSerializer,
    TagSerializer,
)
from users.models import User
from business_account.models import BusinessAccount

# Helper for standardizing API responses
def standard_response(success=True, message="", data=None, errors=None, status_code=status.HTTP_200_OK, headers=None):
    response_data = {
        'success': success,
        'message': message,
    }
    if data is not None:
        response_data['data'] = data
    if errors is not None:
        response_data['errors'] = errors
    return Response(response_data, status=status_code, headers=headers)

class IsAuthorOrReadOnly(IsAuthenticated):
    """
    Custom permission to only allow authors of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return obj.author == request.user

# Tag Views
class TagListCreateView(generics.ListCreateAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny] # Tags can be created by anyone, or consider IsAuthenticated

class TagRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny] # Consider more restrictive permissions for update/delete

# Need Post Views
class NeedPostListCreateView(generics.ListCreateAPIView):
    queryset = NeedPost.objects.all().prefetch_related('images', 'tags') # Add prefetch_related
    serializer_class = NeedPostSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if isinstance(user, User):
            author_content_type = ContentType.objects.get_for_model(User)
        elif isinstance(user, BusinessAccount):
            author_content_type = ContentType.objects.get_for_model(BusinessAccount)
        else:
            # This case should ideally not happen with proper authentication setup
            raise ValueError("Authenticated user is neither a User nor a BusinessAccount.")
        
        serializer.save(
            author_content_type=author_content_type,
            author_object_id=user.id
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return standard_response(
            success=True,
            message="Need posts retrieved successfully",
            data=serializer.data
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return standard_response(
            success=True,
            message="Need post created successfully",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED,
            headers=headers
        )


class NeedPostRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NeedPost.objects.all().prefetch_related('images', 'tags') # Add prefetch_related
    serializer_class = NeedPostSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthorOrReadOnly]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return standard_response(
            success=True,
            message="Need post retrieved successfully",
            data=serializer.data
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly refresh the instance from the database.
            instance = self.get_object()
        
        return standard_response(
            success=True,
            message="Need post updated successfully",
            data=serializer.data
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return standard_response(
            success=True,
            message="Need post deleted successfully",
            status_code=status.HTTP_204_NO_CONTENT
        )

# Offer Post Views
class OfferPostListCreateView(generics.ListCreateAPIView):
    queryset = OfferPost.objects.all().prefetch_related('images', 'tags') # Add prefetch_related
    serializer_class = OfferPostSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        if isinstance(user, User):
            author_content_type = ContentType.objects.get_for_model(User)
        elif isinstance(user, BusinessAccount):
            author_content_type = ContentType.objects.get_for_model(BusinessAccount)
        else:
            raise ValueError("Authenticated user is neither a User nor a BusinessAccount.")
        
        serializer.save(
            author_content_type=author_content_type,
            author_object_id=user.id
        )
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return standard_response(
            success=True,
            message="Offer posts retrieved successfully",
            data=serializer.data
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return standard_response(
            success=True,
            message="Offer post created successfully",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED,
            headers=headers
        )


class OfferPostRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OfferPost.objects.all().prefetch_related('images', 'tags') # Add prefetch_related
    serializer_class = OfferPostSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthorOrReadOnly]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return standard_response(
            success=True,
            message="Offer post retrieved successfully",
            data=serializer.data
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance = self.get_object()
        
        return standard_response(
            success=True,
            message="Offer post updated successfully",
            data=serializer.data
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return standard_response(
            success=True,
            message="Offer post deleted successfully",
            status_code=status.HTTP_204_NO_CONTENT
        )

# Combined Posts List View
class UserAndBusinessPostsListView(generics.ListAPIView):
    serializer_class = UserAndBusinessPostListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Apply prefetch_related to each queryset before combining
        need_posts = NeedPost.objects.all().prefetch_related('images', 'tags')
        offer_posts = OfferPost.objects.all().prefetch_related('images', 'tags')
        
        # Combine and order by created_at
        queryset = sorted(
            list(need_posts) + list(offer_posts),
            key=lambda post: post.created_at,
            reverse=True
        )
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return standard_response(
            success=True,
            message="All posts retrieved successfully",
            data=serializer.data
        )
