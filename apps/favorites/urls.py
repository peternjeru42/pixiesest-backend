from django.urls import path

from .views import (
    AdminFavoriteActionView,
    AdminFavoriteDetailView,
    AdminFavoriteExportView,
    AdminFavoriteListView,
    PublicFavoriteCreateView,
    PublicFavoriteDetailView,
    PublicFavoriteItemAddView,
    PublicFavoriteItemNoteView,
    PublicFavoriteItemRemoveView,
    PublicFavoriteSubmitView,
)

urlpatterns = [
    path("public/collections/<slug:collection_slug>/favorites/", PublicFavoriteCreateView.as_view(), name="public-favorites-create"),
    path("public/favorites/<str:share_token>/", PublicFavoriteDetailView.as_view(), name="public-favorites-detail"),
    path("public/favorites/<uuid:favorite_list_id>/items/", PublicFavoriteItemAddView.as_view(), name="public-favorites-items"),
    path("public/favorites/<uuid:favorite_list_id>/items/<uuid:media_id>/", PublicFavoriteItemRemoveView.as_view(), name="public-favorites-item-remove"),
    path("public/favorites/<uuid:favorite_list_id>/items/<uuid:media_id>/note/", PublicFavoriteItemNoteView.as_view(), name="public-favorites-item-note"),
    path("public/favorites/<uuid:favorite_list_id>/submit/", PublicFavoriteSubmitView.as_view(), name="public-favorites-submit"),
    path("collections/<uuid:collection_id>/favorites/", AdminFavoriteListView.as_view(), name="admin-favorites-list"),
    path("favorites/<uuid:favorite_list_id>/", AdminFavoriteDetailView.as_view(), name="admin-favorites-detail"),
    path("favorites/<uuid:favorite_list_id>/lock/", AdminFavoriteActionView.as_view(action="lock"), name="admin-favorites-lock"),
    path("favorites/<uuid:favorite_list_id>/unlock/", AdminFavoriteActionView.as_view(action="unlock"), name="admin-favorites-unlock"),
    path("favorites/<uuid:favorite_list_id>/archive/", AdminFavoriteActionView.as_view(action="archive"), name="admin-favorites-archive"),
    path("favorites/<uuid:favorite_list_id>/copy-to-set/", AdminFavoriteExportView.as_view(), name="admin-favorites-copy-to-set"),
    path("favorites/<uuid:favorite_list_id>/export/", AdminFavoriteExportView.as_view(), name="admin-favorites-export"),
]
