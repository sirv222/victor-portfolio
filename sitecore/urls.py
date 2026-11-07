from django.urls import path
from . import views

urlpatterns = [
    path ('', views.homepage, name='homepage' ),
    path ('about', views.about, name='about'),
    path ('projects', views.projects, name='projects'),
    path ('skills', views.skills, name='skills'),
    path ('contact', views.contact, name='contact'),
]