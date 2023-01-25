from django.urls import path
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    path('show', views.show, name='show'),
    path('showFile', views.showFile, name='showFile'),
    path('upload', views.upload, name='upload'),
    path('uploadAll', views.uploadAll, name='uploadAll'),
    path('menu', views.menu, name='menu'),
    path('', RedirectView.as_view(url='menu', permanent=True)),
]
