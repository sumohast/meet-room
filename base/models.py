# models.py - Adding Reservation Model
from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta

class Topic(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)  # Renamed from 'update' for consistency
    
    def __str__(self):
        return self.name

class Room(models.Model):
    host = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)  # Renamed from 'descriptions' for consistency
    capacity = models.IntegerField(default=10)
    has_projector = models.BooleanField(default=False)
    has_whiteboard = models.BooleanField(default=False)
    has_video_conference = models.BooleanField(default=False)
    participants = models.ManyToManyField(User, related_name='participants', blank=True)
    created = models.DateTimeField(auto_now_add=True) 
    updated = models.DateTimeField(auto_now=True)  # Renamed from 'update' for consistency
    
    class Meta:
        ordering = ['-updated', '-created']
    
    def __str__(self):
        return self.name
    
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
        available_slots = [slot for slot in business_hours if slot not in booked_slots]
        
        return available_slots

class Reservation(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
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

class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    body = models.TextField()
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated', '-created']

    def __str__(self):
        return self.body[0:50]
    
