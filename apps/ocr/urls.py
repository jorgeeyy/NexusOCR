from django.urls import path

from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('upload/', views.upload_page, name='upload_page'),
    path('process/<str:doc_uuid>/', views.process_upload, name='process_upload'),
    path('doc/<str:doc_uuid>/', views.document_detail, name='document_detail'),
    path('doc/<str:doc_uuid>/download/', views.download_text, name='download_text'),
    path('doc/<str:doc_uuid>/update-text/', views.update_document_text, name='update_document_text'),
    path('doc/<str:doc_uuid>/delete/', views.delete_document, name='delete_document'),
]
