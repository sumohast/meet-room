from django.forms import ModelForm
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import models
from .models import Room, Reservation , TimeSlot
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

class ReservationForm(ModelForm): #
    # تغییر فیلد time_slot به ModelChoiceField یا ChoiceField که به صورت داینامیک پر می‌شود
    time_slot = forms.ChoiceField( # یا ModelChoiceField اگر می‌خواهید مستقیما نمونه TimeSlot را برگردانید
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    
    participant_count = forms.IntegerField( #
        required=True, #
        min_value=1, #
        widget=forms.NumberInput(attrs={'class': 'form-control'}) #
    )
    
    participants_emails = forms.CharField( #
        required=False, #
        widget=forms.Textarea(attrs={ #
            'class': 'form-control', #
            'rows': 2, #
            'placeholder': 'Enter email addresses separated by commas' #
        }) #
    )
    
    class Meta: #
        model = Reservation #
        fields = ['title', 'description', 'date', 'participant_count', 'participants_emails'] #
        widgets = { #
            'title': forms.TextInput(attrs={'class': 'form-control'}), #
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), #
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), #
            'participants_emails': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), #
        } #
    
    def __init__(self, *args, **kwargs): #
        super().__init__(*args, **kwargs) #
        
        # دریافت اسلات‌های زمانی فعال از دیتابیس
        active_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
        # ایجاد choices برای فیلد time_slot
        # مقدار ذخیره شده، رشته "HH:MM-HH:MM" خواهد بود
        self.fields['time_slot'].choices = [
            (slot.formatted_slot, str(slot)) for slot in active_slots
        ]
        
        # اگر مقدار اولیه‌ای برای time_slot از طریق GET پارامتر ارسال شده باشد، آن را انتخاب کنید
        # این بخش برای زمانی است که کاربر از صفحه جزئیات اتاق یا تقویم روی یک اسلات خاص کلیک می‌کند
        if 'initial' in kwargs and 'time_slot' in kwargs['initial']: #
            initial_time_slot_value = kwargs['initial']['time_slot'] #
            # بررسی کنید آیا مقدار اولیه در بین گزینه‌های موجود هست یا خیر
            if any(initial_time_slot_value == choice[0] for choice in self.fields['time_slot'].choices):
                self.fields['time_slot'].initial = initial_time_slot_value
            # اگر قرار است از طریق Query Parameter فقط start و end ارسال شود و نه فرمت "HH:MM-HH:MM"
            # باید منطق initial_time_slot_value را برای تطابق با فرمت ذخیره شده در choices تغییر دهید.

    def clean(self): #
        cleaned_data = super().clean() #
        date_cleaned = cleaned_data.get('date') #
        time_slot_str = cleaned_data.get('time_slot') #
        participant_count = cleaned_data.get('participant_count') #
        room = self.initial.get('room') if hasattr(self, 'initial') and 'room' in self.initial else None #
        
        if date_cleaned and time_slot_str: #
            try:
                start_time_str, end_time_str = time_slot_str.split('-') #
                start_time = datetime.strptime(start_time_str, '%H:%M').time() #
                end_time = datetime.strptime(end_time_str, '%H:%M').time() #
                
                cleaned_data['start_time'] = start_time #
                cleaned_data['end_time'] = end_time #
                
                today = datetime.now().date() #
                current_time = datetime.now().time() #
                
                if date_cleaned < today or (date_cleaned == today and start_time < current_time): #
                    raise forms.ValidationError('Cannot make reservations in the past') #
            except ValueError:
                raise forms.ValidationError("Invalid time slot format.")
                
        if room and participant_count and participant_count > room.capacity: #
            raise forms.ValidationError(f'The number of participants ({participant_count}) exceeds the room capacity ({room.capacity}).') #
        
        return cleaned_data #