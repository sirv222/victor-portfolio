from django.urls import path

from . import views

urlpatterns = [
    path('', views.blog, name='blog'),
    path('login/', views.writer_login, name='login'),
    path('logout/', views.writer_logout, name='logout'),
    path('register/', views.register_writer, name='register_writer'),
    path('verify-email/<uidb64>/<token>/', views.verify_account_email, name='verify_account_email'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/', views.password_reset_done_view, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('reset/done/', views.password_reset_complete_view, name='password_reset_complete'),
    path('dashboard/', views.writer_dashboard, name='writer_dashboard'),
    path('new/', views.create_blog_post, name='create_blog_post'),
    path('settings/', views.account_settings, name='account_settings'),
    path('author/<str:username>/', views.author_profile, name='author_profile'),
    path('post/<slug:slug>/', views.blog_post_detail, name='blog_post_detail'),
    path('post/<slug:slug>/like/', views.toggle_blog_reaction, name='like_blog_post'),
    path('post/<slug:slug>/dislike/', views.toggle_blog_reaction, name='dislike_blog_post'),
    path('post/<slug:slug>/comment/', views.add_blog_comment, name='add_blog_comment'),
]