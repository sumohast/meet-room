# views.py - Adding Reservation Views
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from .models import Room, Topic, Message, Reservation
from .forms import RoomForm, UserCreateForm, ReservationForm

def home(request):
    q = request.GET.get('q', '')
    
    if q:
        rooms = Room.objects.filter(
            Q(topic__name__icontains=q) |
            Q(name__icontains=q) |
            Q(description__icontains=q)
        )
    else:
        rooms = Room.objects.all()
    
    # Pagination
    paginator = Paginator(rooms, 8)  # Show 8 rooms per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    topics = Topic.objects.all()
    room_count = rooms.count()
    recent_messages = Message.objects.filter(
        Q(room__topic__name__icontains=q)
    )[:5]
    
    # Get upcoming reservations for the logged-in user
    upcoming_reservations = []
    if request.user.is_authenticated:
        upcoming_reservations = Reservation.objects.filter(
            user=request.user,
            date__gte=datetime.now().date()
        ).order_by('date', 'start_time')[:3]

    context = {
        'rooms': page_obj, 
        'topics': topics, 
        'room_count': room_count,
        'recent_messages': recent_messages,
        'upcoming_reservations': upcoming_reservations,
    }
    return render(request, 'base/home.html', context)

def about(request):
    return render(request, 'base/about.html')

def room(request, pk):
    room = get_object_or_404(Room, id=pk)
    room_messages = room.message_set.all()
    participants = room.participants.all()
    
    # Get upcoming reservations for this room
    today = datetime.now().date()
    upcoming_reservations = Reservation.objects.filter(
        room=room,
        date__gte=today
    ).order_by('date', 'start_time')[:5]

    if request.method == 'POST':
        if request.user.is_authenticated:
            message = Message.objects.create(
                user=request.user,
                room=room,
                body=request.POST.get('body')
            )
            room.participants.add(request.user)
            return redirect('room', pk=room.id)
        else:
            messages.error(request, "You must be logged in to post messages")
            return redirect('login')

    context = {
        'room': room, 
        'room_messages': room_messages,
        'participants': participants,
        'upcoming_reservations': upcoming_reservations,
    }
    return render(request, 'base/room.html', context)

@login_required
def createRoom(request):
    form = RoomForm()
    topics = Topic.objects.all()
    
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.host = request.user
            
            topic_name = request.POST.get('topic')
            if topic_name:
                topic, created = Topic.objects.get_or_create(name=topic_name)
                room.topic = topic
                
            room.save()
            messages.success(request, 'Room created successfully!')
            return redirect('home')
        else:
            messages.error(request, 'Error creating room. Please check the form.')

    context = {'form': form, 'topics': topics, 'page': 'create-room'}
    return render(request, 'base/room_form.html', context)

@login_required
def updateRoom(request, pk):
    room = get_object_or_404(Room, id=pk)
    form = RoomForm(instance=room)
    topics = Topic.objects.all()
    
    if request.user != room.host:
        messages.error(request, 'You are not allowed to edit this room')
        return redirect('home')

    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            room = form.save(commit=False)
            
            topic_name = request.POST.get('topic')
            if topic_name:
                topic, created = Topic.objects.get_or_create(name=topic_name)
                room.topic = topic
                
            room.save()
            messages.success(request, 'Room updated successfully!')
            return redirect('room', pk=room.id)
        else:
            messages.error(request, 'Error updating room. Please check the form.')

    context = {'form': form, 'topics': topics, 'room': room, 'page': 'update-room'}
    return render(request, 'base/room_form.html', context)

@login_required
def deleteRoom(request, pk):
    room = get_object_or_404(Room, id=pk)
    
    if request.user != room.host:
        messages.error(request, 'You are not allowed to delete this room')
        return redirect('home')
        
    if request.method == 'POST':
        room.delete()
        messages.success(request, 'Room deleted successfully!')
        return redirect('home')
        
    return render(request, 'base/delete.html', {'obj': room, 'type': 'room'})

@login_required
def deleteMessage(request, pk):
    message = get_object_or_404(Message, id=pk)
    
    if request.user != message.user:
        messages.error(request, 'You are not allowed to delete this message')
        return redirect('room', pk=message.room.id)
    
    if request.method == 'POST':
        room_id = message.room.id
        message.delete()
        messages.success(request, 'Message deleted successfully!')
        return redirect('room', pk=room_id)
    
    return render(request, 'base/delete.html', {'obj': message, 'type': 'message'})

# Reservation Views
@login_required
def createReservation(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    form = ReservationForm()
    
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.room = room
            
            # Check for overlapping reservations
            date = form.cleaned_data.get('date')
            start_time = form.cleaned_data.get('start_time')
            end_time = form.cleaned_data.get('end_time')
            
            overlapping = Reservation.objects.filter(
                room=room,
                date=date,
            ).filter(
                Q(start_time__lt=end_time, end_time__gt=start_time)
            )
            
            if overlapping.exists():
                messages.error(request, 'This time slot is already booked')
            else:
                reservation.save()
                room.participants.add(request.user)
                messages.success(request, f'Reservation for {room.name} created successfully!')
                return redirect('user-reservations')
    
    context = {
        'form': form,
        'room': room,
    }
    return render(request, 'base/reservation_form.html', context)

@login_required
def userReservations(request):
    reservations = Reservation.objects.filter(user=request.user).order_by('date', 'start_time')
    
    # Filter by status (upcoming, past)
    status = request.GET.get('status', 'upcoming')
    today = datetime.now().date()
    
    if status == 'past':
        reservations = reservations.filter(date__lt=today)
    else:  # upcoming
        reservations = reservations.filter(date__gte=today)
    
    # Pagination
    paginator = Paginator(reservations, 10)  # Show 10 reservations per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'reservations': page_obj,
        'status': status,
    }
    return render(request, 'base/user_reservations.html', context)

@login_required
def cancelReservation(request, pk):
    reservation = get_object_or_404(Reservation, id=pk)
    
    if request.user != reservation.user:
        messages.error(request, 'You are not allowed to cancel this reservation')
        return redirect('user-reservations')
    
    if request.method == 'POST':
        reservation.delete()
        messages.success(request, 'Reservation cancelled successfully!')
        return redirect('user-reservations')
    
    return render(request, 'base/delete.html', {'obj': reservation, 'type': 'reservation'})

@login_required
def roomCalendar(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    
    # Get date range (default: current week)
    today = datetime.now().date()
    start_date = request.GET.get('start_date', today.isoformat())
    
    try:
        start_date = datetime.fromisoformat(start_date).date()
    except ValueError:
        start_date = today
    
    # Generate date range (7 days)
    dates = [start_date + timedelta(days=i) for i in range(7)]
    
    # Get reservations for the room in this date range
    reservations = Reservation.objects.filter(
        room=room,
        date__gte=dates[0],
        date__lte=dates[-1]
    ).order_by('date', 'start_time')
    
    # Format reservations by date for easier template rendering
    reservation_by_date = {}
    for date in dates:
        reservation_by_date[date] = []
    
    for res in reservations:
        if res.date in reservation_by_date:
            reservation_by_date[res.date].append(res)
    
    context = {
        'room': room,
        'dates': dates,
        'reservations_by_date': reservation_by_date,
        'prev_week': (dates[0] - timedelta(days=7)).isoformat(),
        'next_week': (dates[0] + timedelta(days=7)).isoformat(),
        'today': today.isoformat(),
    }
    return render(request, 'base/room_calendar.html', context)

def loginPage(request):
    page = 'login'
    
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, 'User does not exist')
            return render(request, 'base/login_register.html', {'page': page})
            
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid password')
            
    context = {'page': page}
    return render(request, 'base/login_register.html', context)

def logoutUser(request):
    logout(request)
    return redirect('home')

def registerPage(request):
    form = UserCreateForm()
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
    context = {'form': form}
    return render(request, 'base/login_register.html', context)