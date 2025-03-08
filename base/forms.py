from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Room, Topic

class UserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class RoomForm(ModelForm):
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Room
        fields = ['name', 'topic', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }