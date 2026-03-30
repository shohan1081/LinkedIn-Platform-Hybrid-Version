from django.urls import path
from .views import (
    NeedPostListCreateView,
    NeedPostRetrieveUpdateDestroyView,
    OfferPostListCreateView,
    OfferPostRetrieveUpdateDestroyView,
    UserAndBusinessPostsListView,
    NeedPostProposalCreateView,
    NeedPostProposalCancelView,
    NeedPostProposalListView,
)

app_name = 'posts'

urlpatterns = [
    # Need Posts
    path('needs/', NeedPostListCreateView.as_view(), name='needpost-list-create'),
    path('needs/<uuid:pk>/', NeedPostRetrieveUpdateDestroyView.as_view(), name='needpost-retrieve-update-destroy'),
    
    # Need Post Proposals
    path('needs/<uuid:pk>/propose/', NeedPostProposalCreateView.as_view(), name='needpost-propose'),
    path('needs/<uuid:pk>/proposals/', NeedPostProposalListView.as_view(), name='needpost-proposals'),
    path('proposals/<int:pk>/cancel/', NeedPostProposalCancelView.as_view(), name='proposal-cancel'),

    # Offer Posts
    path('offers/', OfferPostListCreateView.as_view(), name='offerpost-list-create'),
    path('offers/<uuid:pk>/', OfferPostRetrieveUpdateDestroyView.as_view(), name='offerpost-retrieve-update-destroy'),
    
    # Combined Feed
    path('all/', UserAndBusinessPostsListView.as_view(), name='all-posts-list'),
]
