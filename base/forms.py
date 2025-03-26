from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import models
from .models import Room, Reservation
from datetime import datetime, timedelta

# forms.py use to create forms for the application for registration, login, room creation, and reservation creation.

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
    time_slot = forms.CharField(
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    
    participant_count = forms.IntegerField(
        required=True,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
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
        fields = ['title', 'description', 'date', 'participant_count', 'participants_emails']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'participants_emails': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if 'initial' in kwargs and 'time_slot' in kwargs['initial']:
            initial_time_slot = kwargs['initial']['time_slot']
            self.fields['time_slot'].widget.choices = [(initial_time_slot, initial_time_slot)]
        else:
            time_slots = [
            ('06:00-07:00', '06:00 - 07:00'),
            ('07:00-08:00', '07:00 - 08:00'),
            ('08:00-09:00', '08:00 - 09:00'),
            ('09:00-10:00', '09:00 - 10:00'),
            ('10:03-11:00', '10:03 - 11:00'),
            ('11:05-12:00', '11:05 - 12:00'),
            ('12:08-13:00', '12:08 - 13:00'),  # اضافه کردن زمان ناهار
            ('13:00-14:00', '13:00 - 14:00'),
            ('14:00-15:00', '14:00 - 15:00'),
            ('15:00-16:00', '15:00 - 16:00'),
            ('16:00-17:00', '16:00 - 17:00'),
            ('17:00-18:00', '17:00 - 18:00'),  # اضافه کردن زمان‌های عصر
            ('18:03-19:00', '18:03 - 19:00'),
            ('19:00-20:00', '19:00 - 20:00'),
            ('20:20-21:00', '20:20 - 21:00'),  # اضافه کردن زمان‌های شب
            ('21:20-22:00', '21:20 - 22:00'),
        ]
            self.fields['time_slot'].widget.choices = time_slots

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time_slot = cleaned_data.get('time_slot')
        participant_count = cleaned_data.get('participant_count')
        room = self.initial.get('room') if hasattr(self, 'initial') and 'room' in self.initial else None
        
        if date and time_slot:
            # Extract start_time and end_time from time_slot
            start_time_str, end_time_str = time_slot.split('-')
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
            
            # Store these in cleaned_data for the view to use
            cleaned_data['start_time'] = start_time
            cleaned_data['end_time'] = end_time
            
            # Check if the reservation is in the past
            today = datetime.now().date()
            current_time = datetime.now().time()
            
            # Only check for past reservations if date is today and in the past
            if date < today or (date == today and start_time < current_time):
                raise forms.ValidationError('Cannot make reservations in the past')
                # pass
                
        # Check room capacity if room and participant_count are available
        if room and participant_count and participant_count > room.capacity:
            raise forms.ValidationError(f'The number of participants ({participant_count}) exceeds the room capacity ({room.capacity}).')
        
        return cleaned_data