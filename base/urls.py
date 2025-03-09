# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('about/', views.about, name="about"),
    path('room/<str:pk>/', views.room, name="room"),
    
    path('login/', views.loginPage, name="login"),
    path('logout/', views.logoutUser, name="logout"),
    path('register/', views.registerPage, name="register"),
    
    path('create-room/', views.createRoom, name="create-room"),
    path('update-room/<str:pk>/', views.updateRoom, name="update-room"),
    path('delete-room/<str:pk>/', views.deleteRoom, name="delete-room"),
    path('delete-message/<str:pk>/', views.deleteMessage, name="delete-message"),
    
    # Reservation routes
    path('room/<str:room_id>/reserve/', views.createReservation, name="create-reservation"),
    path('room/<str:room_id>/calendar/', views.roomCalendar, name="room-calendar"),
    path('my-reservations/', views.userReservations, name="user-reservations"),
    path('cancel-reservation/<str:pk>/', views.cancelReservation, name="cancel-reservation"),
]