from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
# در models.py در کلاس Reservation


class Room(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField(default=10)
    has_projector = models.BooleanField(default=False)
    has_whiteboard = models.BooleanField(default=False)
    has_video_conference = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True) 
    updated = models.DateTimeField(auto_now=True)  
    
    class Meta: # this class is used to define metadata for the model , for example when we want to sort the rooms by name
        ordering = ['name']
        # ordering = ['-name'] # to sort in descending order
    
    def __str__(self): # this function is used to return a string representation of the object , for example when we want to print the object
        return self.name
    
    def is_available(self, date, start_time, end_time): # this function check if the room is available for the specified time slot
        """Check if room is available for the specified time slot"""
        overlapping = self.reservation_set.filter(
            date=date,
        ).filter(
            models.Q(start_time__lt=end_time, end_time__gt=start_time)
        )
        return not overlapping.exists()
    
    def get_current_status(self): # this function returns the current status of the room (occupied/free)
        """Returns the current status of the room (occupied/free)"""
        now = datetime.now()
        today = now.date()
        current_time = now.time()
        
        active_reservation = self.reservation_set.filter(
            date=today,
            start_time__lte=current_time,
            end_time__gt=current_time
        ).first()
        
        if active_reservation:
            return {
                'status': 'occupied',
                'reservation': active_reservation
            }
        else:
            return {
                'status': 'free',
                'next_reservation': self.reservation_set.filter(
                    date=today,
                    start_time__gt=current_time
                ).order_by('start_time').first()
            }
    
    def get_available_time_slots(self, date): #
        """Returns available time slots for a given date based on defined TimeSlot model."""
        # دریافت تمام اسلات‌های زمانی فعال از دیتابیس
        all_defined_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
        
        if not all_defined_slots.exists():
            return [] # اگر هیچ اسلات زمانی تعریف نشده باشد

        # Get all reservations for this room on the given date
        reservations_for_date = self.reservation_set.filter(date=date) #
        booked_slots_ranges = [(res.start_time, res.end_time) for res in reservations_for_date] #
        
        available_slots_list = []
        for slot in all_defined_slots:
            slot_start, slot_end = slot.start_time, slot.end_time
            is_slot_available = True
            for res_start, res_end in booked_slots_ranges: #
                # Check for overlap
                if res_start < slot_end and res_end > slot_start: #
                    is_slot_available = False #
                    break #
            if is_slot_available: #
                # می‌توانید فرمت مورد نیازتان را برگردانید. اینجا (start_time, end_time) برگردانده شده.
                available_slots_list.append((slot_start, slot_end)) #
        
        return available_slots_list #

class Reservation(models.Model):
    participant_count = models.IntegerField(default=1, help_text="Number of participants")
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    participants_emails = models.TextField(null=True, blank=True, 
                                          help_text="Enter email addresses separated by commas")
    reminder_sent = models.BooleanField(default=False) # this field is used to track if a reminder has been sent for this reservation
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        # Add a constraint to prevent overlapping reservations
        constraints = [
            models.UniqueConstraint(
                fields=['room', 'date', 'start_time'], 
                name='unique_reservation'
            )
        ]
    
    def __str__(self):
        return f"{self.title} - {self.room.name} ({self.date})"
    

    def is_active(self): # this function checks if the reservation is currently active
        """Check if reservation is currently active"""
        now = datetime.now()
        reservation_start = datetime.combine(self.date, self.start_time)
        reservation_end = datetime.combine(self.date, self.end_time)
        return reservation_start <= now <= reservation_end
    
    def get_participant_list(self): # this function returns a list of participant emails
        """Returns list of participant emails"""
        print(f"Getting participant list for reservation: {self.id}")
        print(f"Raw participants_emails field: '{self.participants_emails}'")
        
        if not self.participants_emails:
            print("No participants found")
            return []
        
        emails = [email.strip() for email in self.participants_emails.split(',')]
        print(f"Extracted {len(emails)} email(s): {emails}")
        return emails


class WhiteboardData(models.Model):
    reservation = models.ForeignKey('Reservation', on_delete=models.CASCADE)
    data = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']


class ChatMessage(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.user.username}: {self.message[:20]}"

class TimeSlot(models.Model):
    start_time = models.TimeField(unique=True) # زمان شروع اسلات، باید منحصر به فرد باشد
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True, help_text="فعال بودن اسلات برای نمایش در فرم‌ها")

    class Meta:
        ordering = ['start_time']
        # می‌توانید یک محدودیت اضافه کنید که end_time همیشه بعد از start_time باشد
        constraints = [
            models.CheckConstraint(check=models.Q(end_time__gt=models.F('start_time')), name='end_time_after_start_time')
        ]

    def __str__(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

    @property
    def formatted_slot(self):
        return f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
