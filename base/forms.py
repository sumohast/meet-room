from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import models
from .models import Room, Reservation
from datetime import datetime, timedelta


class UserCreateForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

class RoomForm(ModelForm):
    class Meta:
        model = Room
        fields = ['name', 'description', 'capacity', 'has_projector', 'has_whiteboard', 'has_video_conference']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'has_projector': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_whiteboard': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_video_conference': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ReservationForm(ModelForm):
    participants_emails = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 2, 
            'placeholder': 'Enter email addresses separated by commas'
        })
    )
    
    class Meta:
        model = Reservation
        fields = ['title', 'description', 'date', 'start_time', 'end_time', 'participants_emails']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Meeting title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Meeting description'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        date = cleaned_data.get('date')
        room = cleaned_data.get('room')
        
        # Check if end time is after start time
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('End time must be after start time')
        
        # Check if the reservation is in the past
        if date:
            today = datetime.now().date()
            if date < today:
                raise forms.ValidationError('Cannot make reservations in the past')
            
            # If reservation is for today, check time
            if date == today and start_time and start_time < datetime.now().time():
                raise forms.ValidationError('Cannot make reservations in the past')
        
        # Check for overlapping reservations
        if date and start_time and end_time and room:
            overlapping = Reservation.objects.filter(
                room=room,
                date=date,
            ).exclude(
                pk=self.instance.pk if self.instance and self.instance.pk else None
            ).filter(
                models.Q(start_time__lt=end_time, end_time__gt=start_time)
            )
            
            if overlapping.exists():
                raise forms.ValidationError('This time slot is already booked')
                
        return cleaned_data