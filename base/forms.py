from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from .models import Room, User




class RoomForm(ModelForm):
    class Meta:
        model = Room
        fields = '__all__'
        exclude = ['host', 'participants']


