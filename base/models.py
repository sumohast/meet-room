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
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def is_available(self, date, start_time, end_time):
        """Check if room is available for the specified time slot"""
        overlapping = self.reservation_set.filter(
            date=date,
        ).filter(
            models.Q(start_time__lt=end_time, end_time__gt=start_time)
        )
        return not overlapping.exists()
    
    def get_current_status(self):
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
    
    def get_available_time_slots(self, date):
        """Returns available time slots for a given date"""
        # Define business hours (8 AM to 6 PM, 1-hour slots)
        business_hours = [(datetime.strptime(f"{i}:00", "%H:%M").time(), 
                          datetime.strptime(f"{i+1}:00", "%H:%M").time()) 
                          for i in range(8, 18)]
        
        # Get all reservations for this room on the given date
        reservations = self.reservation_set.filter(date=date)
        booked_slots = [(res.start_time, res.end_time) for res in reservations]
        
        # Filter out booked slots
        available_slots = []
        for start, end in business_hours:
            is_available = True
            for res_start, res_end in booked_slots:
                if res_start < end and res_end > start:
                    is_available = False
                    break
            if is_available:
                available_slots.append((start, end))
        
        return available_slots

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
    reminder_sent = models.BooleanField(default=False)
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
    
    def is_active(self):
        """Check if reservation is currently active"""
        now = datetime.now()
        reservation_start = datetime.combine(self.date, self.start_time)
        reservation_end = datetime.combine(self.date, self.end_time)
        return reservation_start <= now <= reservation_end
    
    def get_participant_list(self):
        """Returns list of participant emails"""
        if not self.participants_emails:
            return []
        return [email.strip() for email in self.participants_emails.split(',')]