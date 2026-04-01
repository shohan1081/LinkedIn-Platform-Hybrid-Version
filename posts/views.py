from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from business_account.backends import BusinessAccountAuthentication, MultiModelJWTAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from .models import NeedPost, OfferPost, Tag, Image, NeedPostProposal
from .serializers import (
    NeedPostSerializer,
    OfferPostSerializer,
    UserAndBusinessPostListSerializer,
    TagSerializer,
    NeedPostProposalSerializer,
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
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        tag_name = self.request.query_params.get('tag')
        if tag_name:
            queryset = queryset.filter(tags__name=tag_name.lower())
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        author_content_type = ContentType.objects.get_for_model(user)
        
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
    authentication_classes = [MultiModelJWTAuthentication]
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
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        tag_name = self.request.query_params.get('tag')
        if tag_name:
            queryset = queryset.filter(tags__name=tag_name.lower())
        return queryset

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
    authentication_classes = [MultiModelJWTAuthentication]
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
    """
    API endpoint to retrieve a feed of posts.
    - Regular users see all NeedPosts and OfferPosts.
    - Business accounts see all NeedPosts and only their own OfferPosts.
    - Supports 'tag' query parameter for filtering.
    """
    serializer_class = UserAndBusinessPostListSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tag_name = self.request.query_params.get('tag')
        
        # Base querysets with prefetching for both Need and Offer posts
        need_posts_qs = NeedPost.objects.all().prefetch_related('images', 'tags')
        offer_posts_qs = OfferPost.objects.all().prefetch_related('images', 'tags')

        # Apply tag filter if provided
        if tag_name:
            need_posts_qs = need_posts_qs.filter(tags__name=tag_name.lower())
            offer_posts_qs = offer_posts_qs.filter(tags__name=tag_name.lower())
        
        # Combine and order by created_at
        queryset = sorted(
            list(need_posts_qs) + list(offer_posts_qs),
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

class MyPostsListView(generics.ListAPIView):
    """
    API endpoint that returns only the posts created by the currently authenticated user.
    """
    serializer_class = UserAndBusinessPostListSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_content_type = ContentType.objects.get_for_model(user)
        
        need_posts_qs = NeedPost.objects.filter(
            author_content_type=user_content_type,
            author_object_id=user.id
        ).prefetch_related('images', 'tags')
        
        offer_posts_qs = OfferPost.objects.filter(
            author_content_type=user_content_type,
            author_object_id=user.id
        ).prefetch_related('images', 'tags')

        queryset = sorted(
            list(need_posts_qs) + list(offer_posts_qs),
            key=lambda post: post.created_at,
            reverse=True
        )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return standard_response(
            success=True,
            message="Your posts retrieved successfully",
            data=serializer.data
        )

class ReceivedProposalsListView(generics.ListAPIView):
    """
    Returns all proposals received for all NeedPosts created by the currently authenticated user.
    """
    serializer_class = NeedPostProposalSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_content_type = ContentType.objects.get_for_model(user)
        
        # Find all NeedPosts authored by the current user
        my_posts_ids = NeedPost.objects.filter(
            author_content_type=user_content_type,
            author_object_id=user.id
        ).values_list('id', flat=True)
        
        # Return proposals for those posts
        return NeedPostProposal.objects.filter(need_post_id__in=my_posts_ids).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return standard_response(
            success=True,
            message="Received proposals retrieved successfully",
            data=serializer.data
        )

from rest_framework.parsers import MultiPartParser, FormParser

# Need Post Proposal Views
class NeedPostProposalCreateView(generics.CreateAPIView):
    """
    API endpoint to submit a proposal for a NeedPost.
    """
    serializer_class = NeedPostProposalSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        need_post_id = self.kwargs.get('pk')
        try:
            need_post = NeedPost.objects.get(pk=need_post_id)
        except NeedPost.DoesNotExist:
            return standard_response(success=False, message="Need post not found.", status_code=status.HTTP_404_NOT_FOUND)

        # Force evaluation and get clean user object/ID/ContentType
        user = request.user
        user_id = str(user.id)
        user_content_type = ContentType.objects.get_for_model(user)

        # Explicitly check if the requesting user is the author
        author_id = str(need_post.author_object_id)
        author_content_type = need_post.author_content_type

        if author_content_type == user_content_type and author_id == user_id:
            return standard_response(success=False, message="You cannot propose to your own post.", status_code=status.HTTP_400_BAD_REQUEST)

        # Check if already proposed
        if NeedPostProposal.objects.filter(need_post=need_post, proposer_content_type=user_content_type, proposer_object_id=user.id).exists():
            return standard_response(success=False, message="You have already submitted a proposal for this post.", status_code=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            need_post=need_post,
            proposer_content_type=user_content_type,
            proposer_object_id=user.id
        )

        return standard_response(
            success=True,
            message="Proposal submitted successfully",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )

class NeedPostProposalCancelView(APIView):
    """
    API endpoint to cancel a proposal.
    Supports passing either the Proposal ID or the NeedPost ID.
    """
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # Force evaluation
        user = request.user
        user_id = str(user.id)
        user_content_type = ContentType.objects.get_for_model(user)

        # Try to find proposal by its own ID first, then by NeedPost ID
        proposal = NeedPostProposal.objects.filter(
            Q(pk=pk) | Q(need_post_id=pk),
            proposer_content_type=user_content_type,
            proposer_object_id=user.id
        ).first()

        if not proposal:
            return standard_response(
                success=False, 
                message="Proposal not found or you are not authorized to cancel it.", 
                status_code=status.HTTP_404_NOT_FOUND
            )

        if proposal.status == 'cancelled':
            return standard_response(success=False, message="Proposal is already cancelled.", status_code=status.HTTP_400_BAD_REQUEST)

        proposal.status = 'cancelled'
        proposal.save()

        return standard_response(success=True, message="Proposal cancelled successfully.")

class NeedPostProposalListView(generics.ListAPIView):
    """
    API endpoint to list proposals for a specific NeedPost.
    Only the author of the post can see all proposals.
    """
    serializer_class = NeedPostProposalSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        need_post_id = self.kwargs.get('pk')
        return NeedPostProposal.objects.filter(need_post_id=need_post_id)

    def list(self, request, *args, **kwargs):
        need_post_id = self.kwargs.get('pk')
        try:
            need_post = NeedPost.objects.get(pk=need_post_id)
        except NeedPost.DoesNotExist:
            return standard_response(success=False, message="Need post not found.", status_code=status.HTTP_404_NOT_FOUND)

        # Force evaluation
        user = request.user
        user_id = str(user.id)
        user_content_type = ContentType.objects.get_for_model(user)

        # Explicitly check if the requesting user is the author
        author_id = str(need_post.author_object_id)
        author_content_type = need_post.author_content_type

        if author_content_type != user_content_type or author_id != user_id:
            return standard_response(success=False, message="You are not authorized to view proposals for this post.", status_code=status.HTTP_403_FORBIDDEN)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return standard_response(
            success=True,
            message="Proposals retrieved successfully",
            data=serializer.data
        )
