from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('room/<str:pk>/', views.room_detail, name="room-detail"),
    path('room/<str:room_id>/calendar/', views.room_calendar, name="room-calendar"),
    
    # Reservation routes
    path('room/<str:room_id>/reserve/', views.create_reservation, name="create-reservation"),
    path('my-reservations/', views.user_reservations, name="user-reservations"),
    path('cancel-reservation/<int:reservation_id>/', views.cancel_reservation, name='cancel-reservation'),
    
    # Admin routes
    path('admin-dashboard/', views.admin_dashboard, name="admin-dashboard"),
    path('admin-reservations/', views.admin_reservations, name="admin-reservations"),
    path('room-management/', views.room_management, name="room-management"),
    path('create-room/', views.create_room, name="create-room"),
    path('update-room/<str:pk>/', views.update_room, name="update-room"),
    path('delete-room/<str:pk>/', views.delete_room, name="delete-room"),
    path('about' , views.about, name="about"),
    
    # Authentication
    path('login/', views.login_page, name="login"),
    path('logout/', views.logout_user, name="logout"),
    path('register/', views.register_page, name="register"),
    # Removed the quick-reserve URL pattern
]