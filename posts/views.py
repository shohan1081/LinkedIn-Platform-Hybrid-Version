import random
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from business_account.backends import BusinessAccountAuthentication, MultiModelJWTAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from .models import NeedPost, OfferPost, Tag, Image, NeedPostProposal, OfferPostProposal
from .serializers import (
    NeedPostSerializer,
    OfferPostSerializer,
    UserAndBusinessPostListSerializer,
    TagSerializer,
    NeedPostProposalSerializer,
    OfferPostProposalSerializer,
)
from chat.models import Conversation, Message
from users.models import User, Follow
from business_account.models import BusinessAccount
from notifications.services import create_notification

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
        queryset = super().get_queryset().order_by('-created_at')
        tag_name = self.request.query_params.get('tag')
        if tag_name:
            queryset = queryset.filter(tags__name=tag_name.lower())
        
        posts = list(queryset)
        recent_posts = posts[:10]
        older_posts = posts[10:]
        random.shuffle(older_posts)
        return recent_posts + older_posts

    def perform_create(self, serializer):
        user = self.request.user
        author_content_type = ContentType.objects.get_for_model(user)
        
        post = serializer.save(
            author_content_type=author_content_type,
            author_object_id=user.id
        )

        # Notify followers
        followers_qs = Follow.objects.filter(
            followed_content_type=author_content_type,
            followed_object_id=user.id
        )

        sender_name = "Someone"
        if hasattr(user, 'first_name'):
            sender_name = f"{user.first_name} {user.last_name}".strip() or user.email
        else:
            sender_name = getattr(user, 'business_name', user.email)

        for follow in followers_qs:
            create_notification(
                recipient=follow.follower,
                title="New Post Activity",
                message=f"{sender_name} created a new need post: {post.title}",
                notification_type='new_post',
                target=post
            )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
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
        serializer = self.get_serializer(instance, context={'request': request})
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
            status_code=status.HTTP_200_OK
        )

# Offer Post Views
class OfferPostListCreateView(generics.ListCreateAPIView):
    queryset = OfferPost.objects.all().prefetch_related('images', 'tags') # Add prefetch_related
    serializer_class = OfferPostSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        tag_name = self.request.query_params.get('tag')
        if tag_name:
            queryset = queryset.filter(tags__name=tag_name.lower())
        
        posts = list(queryset)
        recent_posts = posts[:10]
        older_posts = posts[10:]
        random.shuffle(older_posts)
        return recent_posts + older_posts

    def perform_create(self, serializer):
        user = self.request.user
        if isinstance(user, User):
            author_content_type = ContentType.objects.get_for_model(User)
        elif isinstance(user, BusinessAccount):
            author_content_type = ContentType.objects.get_for_model(BusinessAccount)
        else:
            raise ValueError("Authenticated user is neither a User nor a BusinessAccount.")
        
        post = serializer.save(
            author_content_type=author_content_type,
            author_object_id=user.id
        )

        # Notify followers
        followers_qs = Follow.objects.filter(
            followed_content_type=author_content_type,
            followed_object_id=user.id
        )

        sender_name = "Someone"
        if hasattr(user, 'first_name'):
            sender_name = f"{user.first_name} {user.last_name}".strip() or user.email
        else:
            sender_name = getattr(user, 'business_name', user.email)

        for follow in followers_qs:
            create_notification(
                recipient=follow.follower,
                title="New Post Activity",
                message=f"{sender_name} created a new offer post: {post.title}",
                notification_type='new_post',
                target=post
            )
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
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
        serializer = self.get_serializer(instance, context={'request': request})
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
        all_posts = sorted(
            list(need_posts_qs) + list(offer_posts_qs),
            key=lambda post: post.created_at,
            reverse=True
        )

        # Logic: 10 recent posts first, then shuffle the rest
        recent_posts = all_posts[:10]
        older_posts = all_posts[10:]
        random.shuffle(older_posts)
        
        return recent_posts + older_posts
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
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
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return standard_response(
            success=True,
            message="Your posts retrieved successfully",
            data=serializer.data
        )

class ReceivedProposalsListView(generics.ListAPIView):
    """
    Returns all proposals received for all posts (Need and Offer) created by the currently authenticated user.
    """
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # We'll handle combining and serializing in the list method
        return None

    def list(self, request, *args, **kwargs):
        user = self.request.user
        user_content_type = ContentType.objects.get_for_model(user)
        
        # Need Post Proposals
        my_needs_ids = NeedPost.objects.filter(
            author_content_type=user_content_type,
            author_object_id=user.id
        ).values_list('id', flat=True)
        need_proposals = NeedPostProposal.objects.filter(need_post_id__in=my_needs_ids)
        
        # Offer Post Proposals
        my_offers_ids = OfferPost.objects.filter(
            author_content_type=user_content_type,
            author_object_id=user.id
        ).values_list('id', flat=True)
        offer_proposals = OfferPostProposal.objects.filter(offer_post_id__in=my_offers_ids)

        # Combine and sort
        combined = sorted(
            list(need_proposals) + list(offer_proposals),
            key=lambda p: p.created_at,
            reverse=True
        )

        # Manual serialization
        data = []
        for p in combined:
            if isinstance(p, NeedPostProposal):
                ser = NeedPostProposalSerializer(p, context={'request': request})
                item = ser.data
                item['proposal_type'] = 'need'
            else:
                ser = OfferPostProposalSerializer(p, context={'request': request})
                item = ser.data
                item['proposal_type'] = 'offer'
            data.append(item)

        return standard_response(
            success=True,
            message="Received proposals retrieved successfully",
            data=data
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

        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        proposal = serializer.save(
            need_post=need_post,
            proposer_content_type=user_content_type,
            proposer_object_id=user.id
        )

        # Create a Message Request (Conversation)
        conversation, created = Conversation.objects.get_or_create(
            part1_content_type=need_post.author_content_type,
            part1_object_id=need_post.author_object_id,
            part2_content_type=user_content_type,
            part2_object_id=user.id,
            post_content_type=ContentType.objects.get_for_model(need_post),
            post_object_id=need_post.id
        )
        
        # Add initial message
        initial_text = f"Connect Request for: {need_post.title}\n\nSubject: {proposal.subject}\nMessage: {proposal.message}"
        Message.objects.create(
            conversation=conversation,
            sender_content_type=user_content_type,
            sender_object_id=user.id,
            text=initial_text
        )

        return standard_response(
            success=True,
            message="Proposal submitted successfully",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )

class ProposalCancelView(APIView):
    """
    API endpoint to cancel a proposal.
    Supports both NeedPost and OfferPost proposals.
    Supports passing either the Proposal ID or the Post ID.
    """
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # Force evaluation
        user = request.user
        user_content_type = ContentType.objects.get_for_model(user)
        target_id_str = str(pk)
        
        # 1. Search in NeedPostProposals
        need_proposal = None
        need_proposals_qs = NeedPostProposal.objects.filter(
            proposer_content_type=user_content_type,
            proposer_object_id=user.id
        )
        for p in need_proposals_qs:
            if str(p.id) == target_id_str or str(p.need_post_id) == target_id_str:
                need_proposal = p
                break
        
        if need_proposal:
            if need_proposal.status == 'cancelled':
                return standard_response(success=False, message="Proposal is already cancelled.", status_code=status.HTTP_400_BAD_REQUEST)
            need_proposal.status = 'cancelled'
            need_proposal.save()
            return standard_response(success=True, message="Proposal cancelled successfully.")

        # 2. Search in OfferPostProposals
        offer_proposal = None
        offer_proposals_qs = OfferPostProposal.objects.filter(
            proposer_content_type=user_content_type,
            proposer_object_id=user.id
        )
        for p in offer_proposals_qs:
            if str(p.id) == target_id_str or str(p.offer_post_id) == target_id_str:
                offer_proposal = p
                break
        
        if offer_proposal:
            if offer_proposal.status == 'cancelled':
                return standard_response(success=False, message="Inquiry is already cancelled.", status_code=status.HTTP_400_BAD_REQUEST)
            offer_proposal.status = 'cancelled'
            offer_proposal.save()
            return standard_response(success=True, message="Inquiry cancelled successfully.")

        return standard_response(
            success=False, 
            message="Proposal not found or you are not authorized to cancel it.", 
            status_code=status.HTTP_404_NOT_FOUND
        )

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
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return standard_response(
            success=True,
            message="Proposals retrieved successfully",
            data=serializer.data
        )

class SinglePostDetailView(generics.RetrieveAPIView):
    """
    Retrieve any post (Need or Offer) by its UUID.
    This works for both types and is accessible to any authenticated user.
    """
    serializer_class = UserAndBusinessPostListSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        pk = self.kwargs.get('pk')
        
        # Try NeedPost
        try:
            return NeedPost.objects.get(pk=pk)
        except NeedPost.DoesNotExist:
            pass
            
        # Try OfferPost
        try:
            return OfferPost.objects.get(pk=pk)
        except OfferPost.DoesNotExist:
            raise status.HTTP_404_NOT_FOUND

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            if isinstance(instance, int) and instance == status.HTTP_404_NOT_FOUND:
                 return standard_response(success=False, message="Post not found.", status_code=status.HTTP_404_NOT_FOUND)
        except Exception:
             return standard_response(success=False, message="Post not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance, context={'request': request})
        return standard_response(
            success=True,
            message="Post details retrieved successfully",
            data=serializer.data
        )

from .models import OfferPostProposal
from .serializers import OfferPostProposalSerializer

class OfferPostProposalCreateView(generics.CreateAPIView):
    """
    API endpoint to submit a proposal/inquiry for an OfferPost.
    """
    serializer_class = OfferPostProposalSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        offer_post_id = self.kwargs.get('pk')
        try:
            offer_post = OfferPost.objects.get(pk=offer_post_id)
        except OfferPost.DoesNotExist:
            return standard_response(success=False, message="Offer post not found.", status_code=status.HTTP_404_NOT_FOUND)

        # Force evaluation and get clean user object/ID/ContentType
        user = request.user
        user_id = str(user.id)
        user_content_type = ContentType.objects.get_for_model(user)

        # Explicitly check if the requesting user is the author
        author_id = str(offer_post.author_object_id)
        author_content_type = offer_post.author_content_type

        if author_content_type == user_content_type and author_id == user_id:
            return standard_response(success=False, message="You cannot propose to your own offer.", status_code=status.HTTP_400_BAD_REQUEST)

        # Check if already proposed
        if OfferPostProposal.objects.filter(offer_post=offer_post, proposer_content_type=user_content_type, proposer_object_id=user.id).exists():
            return standard_response(success=False, message="You have already submitted an inquiry for this offer.", status_code=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        proposal = serializer.save(
            offer_post=offer_post,
            proposer_content_type=user_content_type,
            proposer_object_id=user.id
        )

        # Create a Message Request (Conversation)
        conversation, created = Conversation.objects.get_or_create(
            part1_content_type=offer_post.author_content_type,
            part1_object_id=offer_post.author_object_id,
            part2_content_type=user_content_type,
            part2_object_id=user.id,
            post_content_type=ContentType.objects.get_for_model(offer_post),
            post_object_id=offer_post.id
        )
        
        # Add initial message
        initial_text = f"Inquiry for: {offer_post.title}\n\nSubject: {proposal.subject}\nMessage: {proposal.message}"
        if proposal.budget:
            initial_text += f"\nBudget: {proposal.budget}"
        if proposal.expected_delivery:
            initial_text += f"\nExpected Delivery: {proposal.expected_delivery}"
            
        Message.objects.create(
            conversation=conversation,
            sender_content_type=user_content_type,
            sender_object_id=user.id,
            text=initial_text
        )

        return standard_response(
            success=True,
            message="Proposal/Inquiry submitted successfully",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )

class OfferPostProposalListView(generics.ListAPIView):
    """
    API endpoint to list proposals for a specific OfferPost.
    Only the author of the post can see all proposals.
    """
    serializer_class = OfferPostProposalSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        offer_post_id = self.kwargs.get('pk')
        return OfferPostProposal.objects.filter(offer_post_id=offer_post_id)

    def list(self, request, *args, **kwargs):
        offer_post_id = self.kwargs.get('pk')
        try:
            offer_post = OfferPost.objects.get(pk=offer_post_id)
        except OfferPost.DoesNotExist:
            return standard_response(success=False, message="Offer post not found.", status_code=status.HTTP_404_NOT_FOUND)

        # Force evaluation
        user = request.user
        user_id = str(user.id)
        user_content_type = ContentType.objects.get_for_model(user)

        # Explicitly check if the requesting user is the author
        author_id = str(offer_post.author_object_id)
        author_content_type = offer_post.author_content_type

        if author_content_type != user_content_type or author_id != user_id:
            return standard_response(success=False, message="You are not authorized to view proposals for this offer.", status_code=status.HTTP_403_FORBIDDEN)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return standard_response(
            success=True,
            message="Proposals retrieved successfully",
            data=serializer.data
        )

class ProposalActionView(APIView):
    """
    API endpoint to accept or reject a proposal (for both Need and Offer posts).
    Only the author of the post can perform this action.
    """
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # Force evaluation
        user = request.user
        user_id = str(user.id)
        user_content_type = ContentType.objects.get_for_model(user)
        target_id_str = str(pk)

        action = request.data.get('action') # 'accept' or 'reject'
        if action not in ['accept', 'reject']:
            return standard_response(success=False, message="Invalid action. Use 'accept' or 'reject'.", status_code=status.HTTP_400_BAD_REQUEST)

        # 1. Search in NeedPostProposals
        need_proposal = None
        try:
            need_proposal = NeedPostProposal.objects.get(pk=pk)
            # Check if the requesting user is the author of the NEED POST
            need_post = need_proposal.need_post
            author_id = str(need_post.author_object_id)
            author_content_type = need_post.author_content_type

            if author_content_type != user_content_type or author_id != user_id:
                return standard_response(success=False, message="You are not authorized to perform this action.", status_code=status.HTTP_403_FORBIDDEN)
            
            need_proposal.status = 'accepted' if action == 'accept' else 'rejected'
            need_proposal.save()

            if action == 'accept':
                # Update status to active
                conv_qs = Conversation.objects.filter(
                    part1_content_type=need_post.author_content_type,
                    part1_object_id=need_post.author_object_id,
                    part2_content_type=need_proposal.proposer_content_type,
                    part2_object_id=need_proposal.proposer_object_id,
                    post_content_type=ContentType.objects.get_for_model(need_post),
                    post_object_id=need_post.id
                )
                conv_qs.update(status='active')
                
                # Send welcome message from Author to Proposer
                conversation = conv_qs.first()
                if conversation:
                    welcome_text = f"Hello! I have accepted your connect request for '{need_post.title}'. Let's discuss further."
                    Message.objects.create(
                        conversation=conversation,
                        sender_content_type=need_post.author_content_type,
                        sender_object_id=need_post.author_object_id,
                        text=welcome_text
                    )
                    
                    return standard_response(
                        success=True, 
                        message="Proposal accepted successfully.", 
                        data={"conversation_id": str(conversation.id)}
                    )

            return standard_response(success=True, message=f"Proposal {action}ed successfully.")
        except (NeedPostProposal.DoesNotExist, ValidationError):
            pass

        # 2. Search in OfferPostProposals
        offer_proposal = None
        try:
            offer_proposal = OfferPostProposal.objects.get(pk=pk)
            # Check if the requesting user is the author of the OFFER POST
            offer_post = offer_proposal.offer_post
            author_id = str(offer_post.author_object_id)
            author_content_type = offer_post.author_content_type

            if author_content_type != user_content_type or author_id != user_id:
                return standard_response(success=False, message="You are not authorized to perform this action.", status_code=status.HTTP_403_FORBIDDEN)
            
            offer_proposal.status = 'accepted' if action == 'accept' else 'rejected'
            offer_proposal.save()

            if action == 'accept':
                # Update status to active
                conv_qs = Conversation.objects.filter(
                    part1_content_type=offer_post.author_content_type,
                    part1_object_id=offer_post.author_object_id,
                    part2_content_type=offer_proposal.proposer_content_type,
                    part2_object_id=offer_proposal.proposer_object_id,
                    post_content_type=ContentType.objects.get_for_model(offer_post),
                    post_object_id=offer_post.id
                )
                conv_qs.update(status='active')

                # Send welcome message from Author to Proposer
                conversation = conv_qs.first()
                if conversation:
                    welcome_text = f"Hello! I am interested in your inquiry regarding '{offer_post.title}'. Let's discuss."
                    Message.objects.create(
                        conversation=conversation,
                        sender_content_type=offer_post.author_content_type,
                        sender_object_id=offer_post.author_object_id,
                        text=welcome_text
                    )
                    
                    return standard_response(
                        success=True, 
                        message="Inquiry accepted successfully.", 
                        data={"conversation_id": str(conversation.id)}
                    )

            return standard_response(success=True, message=f"Proposal {action}ed successfully.")
        except (OfferPostProposal.DoesNotExist, ValidationError):
            pass

        return standard_response(success=False, message="Proposal not found.", status_code=status.HTTP_404_NOT_FOUND)
