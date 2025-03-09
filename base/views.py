from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, date, timedelta
from .models import Room, Reservation
from .forms import RoomForm, UserCreateForm, ReservationForm

def home(request):
    # Query all rooms
    rooms = Room.objects.all()
    
    # Add current status to each room
    for room in rooms:
        room.current_status = room.get_current_status()
    
    # Get upcoming reservations for the logged-in user
    upcoming_reservations = []
    if request.user.is_authenticated:
        upcoming_reservations = Reservation.objects.filter(
            user=request.user,
            date__gte=datetime.now().date()
        ).order_by('date', 'start_time')[:3]

    context = {
        'rooms': rooms, 
        'upcoming_reservations': upcoming_reservations,
    }
    return render(request, 'base/home.html', context)

def room_detail(request, pk):
    room = get_object_or_404(Room, id=pk)
    
    # Get current status
    current_status = room.get_current_status()
    
    # Get today's date
    today = datetime.now().date()
    
    # Get available time slots for today
    available_slots = room.get_available_time_slots(today)
    
    # Get upcoming reservations for this room
    upcoming_reservations = Reservation.objects.filter(
        room=room,
        date__gte=today
    ).order_by('date', 'start_time')[:5]

    context = {
        'room': room, 
        'current_status': current_status,
        'available_slots': available_slots,
        'today': today,
        'upcoming_reservations': upcoming_reservations,
    }
    return render(request, 'base/room_detail.html', context)

@login_required
def room_calendar(request, room_id):
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

@login_required
def create_reservation(request, room_id):
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
            
            if not room.is_available(date, start_time, end_time):
                messages.error(request, 'This time slot is already booked')
            else:
                reservation.save()
                messages.success(request, f'Reservation for {room.name} created successfully!')
                return redirect('user-reservations')
    
    context = {
        'form': form,
        'room': room,
    }
    return render(request, 'base/reservation_form.html', context)

@login_required
def user_reservations(request):
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
def cancel_reservation(request, pk):
    reservation = get_object_or_404(Reservation, id=pk)
    
    # Only allow cancellation if user is the creator or staff member
    if request.user != reservation.user and not request.user.is_staff:
        messages.error(request, 'You are not allowed to cancel this reservation')
        return redirect('user-reservations')
    
    if request.method == 'POST':
        reservation.delete()
        messages.success(request, 'Reservation cancelled successfully!')
        if request.user.is_staff:
            return redirect('admin-reservations')
        return redirect('user-reservations')
    
    return render(request, 'base/delete.html', {'obj': reservation, 'type': 'reservation'})

# Admin Views
@staff_member_required
def admin_dashboard(request):
    rooms = Room.objects.all()
    
    # Count total reservations
    total_reservations = Reservation.objects.count()
    
    # Count today's reservations
    today = datetime.now().date()
    today_reservations = Reservation.objects.filter(date=today).count()
    
    # Add current status to each room
    for room in rooms:
        room.current_status = room.get_current_status()
    
    context = {
        'rooms': rooms,
        'total_reservations': total_reservations,
        'today_reservations': today_reservations,
    }
    return render(request, 'base/admin_dashboard.html', context)

@staff_member_required
def admin_reservations(request):
    # Get filter parameters
    room_id = request.GET.get('room', '')
    user_id = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Convert date strings to date objects if provided
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            date_from = ''
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            date_to = ''
    
    # Base queryset
    reservations = Reservation.objects.all().order_by('date', 'start_time')
    
    # Apply filters
    if room_id:
        reservations = reservations.filter(room_id=room_id)
    
    if user_id:
        reservations = reservations.filter(user_id=user_id)
    
    if date_from:
        reservations = reservations.filter(date__gte=date_from)
    
    if date_to:
        reservations = reservations.filter(date__lte=date_to)
    
    # Get all rooms and users for filter dropdowns
    rooms = Room.objects.all()
    users = User.objects.all()
    
    # Pagination
    paginator = Paginator(reservations, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'reservations': page_obj,
        'rooms': rooms,
        'users': users,
        'selected_room': room_id,
        'selected_user': user_id,
        'date_from': date_from.strftime('%Y-%m-%d') if isinstance(date_from, date) else '',
        'date_to': date_to.strftime('%Y-%m-%d') if isinstance(date_to, date) else '',
    }
    
    return render(request, 'base/admin_reservations.html', context)

@staff_member_required
def room_management(request):
    rooms = Room.objects.all()
    return render(request, 'base/room_management.html', {'rooms': rooms})

@staff_member_required
def create_room(request):
    form = RoomForm()
    
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Room created successfully!')
            return redirect('room-management')
    
    context = {'form': form}
    return render(request, 'base/room_form.html', context)

@staff_member_required
def update_room(request, pk):
    room = get_object_or_404(Room, id=pk)
    form = RoomForm(instance=room)
    
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, 'Room updated successfully!')
            return redirect('room-management')
    
    context = {'form': form, 'room': room}
    return render(request, 'base/room_form.html', context)

@staff_member_required
def delete_room(request, pk):
    room = get_object_or_404(Room, id=pk)
    
    if request.method == 'POST':
        room.delete()
        messages.success(request, 'Room deleted successfully!')
        return redirect('room-management')
    
    return render(request, 'base/delete.html', {'obj': room, 'type': 'room'})

# Email reminder function (to be scheduled with a task scheduler like Celery)
def send_reservation_reminders():
    """Send email reminders for upcoming reservations"""
    # Get reservations for tomorrow
    tomorrow = datetime.now().date() + timedelta(days=1)
    upcoming_reservations = Reservation.objects.filter(
        date=tomorrow,
        reminder_sent=False
    )
    
    for reservation in upcoming_reservations:
        participants = reservation.get_participant_list()
        if participants:
            subject = f"Reminder: Meeting in {reservation.room.name} tomorrow"
            message = f"""
            Hello,
            
            This is a reminder that you have a meeting scheduled for tomorrow:
            
            Title: {reservation.title}
            Room: {reservation.room.name}
            Date: {reservation.date}
            Time: {reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}
            
            Description:
            {reservation.description}
            
            Please be on time.
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=participants,
                fail_silently=False,
            )
            
            # Mark as sent
            reservation.reminder_sent = True
            reservation.save()

# Authentication Views
def login_page(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, 'User does not exist')
            return render(request, 'base/login.html')
            
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid password')
            
    return render(request, 'base/login.html')

def logout_user(request):
    logout(request)
    return redirect('home')

def register_page(request):
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
    return render(request, 'base/register.html', context)