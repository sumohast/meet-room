from django.contrib import admin
from .models import Room, Reservation, TimeSlot

# Register your models here
admin.site.register(Room)
admin.site.register(Reservation)
admin.site.register(TimeSlot)