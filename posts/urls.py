from django.urls import path
from .views import (
    NeedPostListCreateView,
    NeedPostRetrieveUpdateDestroyView,
    OfferPostListCreateView,
    OfferPostRetrieveUpdateDestroyView,
    UserAndBusinessPostsListView,
    MyPostsListView,
    NeedPostProposalCreateView,
    ProposalCancelView,
    NeedPostProposalListView,
    ReceivedProposalsListView,
    SinglePostDetailView,
    OfferPostProposalCreateView,
    OfferPostProposalListView,
    ProposalActionView,
)

app_name = 'posts'

urlpatterns = [
    # Need Posts
    path('needs/', NeedPostListCreateView.as_view(), name='needpost-list-create'),
    path('needs/<uuid:pk>/', NeedPostRetrieveUpdateDestroyView.as_view(), name='needpost-retrieve-update-destroy'),
    
    # Need Post Proposals
    path('needs/<uuid:pk>/propose/', NeedPostProposalCreateView.as_view(), name='needpost-propose'),
    path('needs/<uuid:pk>/proposals/', NeedPostProposalListView.as_view(), name='needpost-proposals'),
    
    # Offer Post Proposals (Inquiries)
    path('offers/<uuid:pk>/propose/', OfferPostProposalCreateView.as_view(), name='offerpost-propose'),
    path('offers/<uuid:pk>/proposals/', OfferPostProposalListView.as_view(), name='offerpost-proposals'),
    
    # Shared Proposal Endpoints
    path('proposals/received/', ReceivedProposalsListView.as_view(), name='proposals-received'),
    path('proposals/<uuid:pk>/cancel/', ProposalCancelView.as_view(), name='proposal-cancel'),
    path('proposals/<uuid:pk>/action/', ProposalActionView.as_view(), name='proposal-action'),

    # Offer Posts
    path('offers/', OfferPostListCreateView.as_view(), name='offerpost-list-create'),
    path('offers/<uuid:pk>/', OfferPostRetrieveUpdateDestroyView.as_view(), name='offerpost-retrieve-update-destroy'),
    
    # Combined Feed
    path('all/', UserAndBusinessPostsListView.as_view(), name='all-posts-list'),
    path('my-posts/', MyPostsListView.as_view(), name='my-posts-list'),
    path('<uuid:pk>/', SinglePostDetailView.as_view(), name='post-detail'),
]
