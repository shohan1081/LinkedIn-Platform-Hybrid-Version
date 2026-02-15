from django.urls import path
from .views import (
    NeedPostListCreateView,
    NeedPostRetrieveUpdateDestroyView,
    OfferPostListCreateView,
    OfferPostRetrieveUpdateDestroyView,
    UserAndBusinessPostsListView,
)

app_name = 'posts'

urlpatterns = [
    path('needs/', NeedPostListCreateView.as_view(), name='needpost-list-create'),
    path('needs/<uuid:pk>/', NeedPostRetrieveUpdateDestroyView.as_view(), name='needpost-retrieve-update-destroy'),
    path('offers/', OfferPostListCreateView.as_view(), name='offerpost-list-create'),
    path('offers/<uuid:pk>/', OfferPostRetrieveUpdateDestroyView.as_view(), name='offerpost-retrieve-update-destroy'),
    path('all/', UserAndBusinessPostsListView.as_view(), name='all-posts-list'),
]