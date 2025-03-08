from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Topic(models.Model):
    name = models.CharField(max_length=100)
    #descriptions = models.TextField(null=True , blank=True)
    created = models.DateTimeField(auto_now_add=True) # this is the date and time the room was created and not changed
    update = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Room(models.Model):
    host = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=100)
    descriptions = models.TextField(null=True , blank=True)
    created = models.DateTimeField(auto_now_add=True) 
    update = models.DateTimeField(auto_now=True)
    #capacity = 
    
    
    def __str__(self):
        return self.name

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