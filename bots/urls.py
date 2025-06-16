from django.urls import path
from . import views

urlpatterns = [
    # Bot management URLs
    path('', views.BotListView.as_view(), name='bot_list'),
    path('create/', views.BotCreateView.as_view(), name='bot_create'),
    path('edit/<uuid:pk>/', views.BotEditView.as_view(), name='bot_edit'),
    path('delete/<uuid:pk>/', views.BotDeleteView.as_view(), name='bot_delete'),
    
    # Chat URLs
    path('chat/<uuid:bot_id>/', views.ChatView.as_view(), name='chat'),
    path('chat/<uuid:bot_id>/send/', views.SendMessageView.as_view(), name='send_message'),
    path('chat/<uuid:bot_id>/clear/', views.ClearConversationView.as_view(), name='clear_conversation'),
]
