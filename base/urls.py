from django.urls import path
from base.views import home, about, room , createRoom , updateRoom

urlpatterns = [
    path('', home , name="home"), # this is the home page
    path('create-room/' , createRoom , name="create-room") , 
    path('room/<str:pk>', room , name="room"), # this is the room page
    path('update-room/<str:pk>' , updateRoom , name='update-room' ),
    path('about/', about , name="about"), # this is the about page
]
