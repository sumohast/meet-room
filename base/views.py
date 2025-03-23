from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, date, timedelta
from .models import Room, Reservation
from .forms import RoomForm, UserCreateForm, ReservationForm
from django.db import models
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


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
    
    # Calculate total reservations for today with active participants count
    today_reservations = Reservation.objects.filter(
        room=room,
        date=today
    )
    
    # Check if the room is at full capacity for today
    room_is_full = False
    active_reservation = None
    if current_status['status'] == 'occupied':
        active_reservation = current_status['reservation']
        if hasattr(active_reservation, 'participant_count') and active_reservation.participant_count >= room.capacity:
            room_is_full = True

    context = {
        'room': room, 
        'current_status': current_status,
        'available_slots': available_slots,
        'today': today,
        'upcoming_reservations': upcoming_reservations,
        'room_is_full': room_is_full,
        'active_reservation': active_reservation,
    }
    return render(request, 'base/room_detail.html', context)

@login_required # this decorator ensures that the user is logged in before accessing the view
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
    
    # Get initial data from query parameters
    initial_data = {
        'room': room,  # Pass the room object to the form
    }
    
    if request.GET.get('date'):
        initial_data['date'] = request.GET.get('date')
    
    # Handle time slot from query parameters
    start_time = request.GET.get('start')
    end_time = request.GET.get('end')
    if start_time and end_time:
        initial_data['time_slot'] = f"{start_time}-{end_time}"
    
    if request.method == 'POST':
        # Print POST data for debugging
        print(f"POST data: {request.POST}")
        
        form = ReservationForm(request.POST, initial=initial_data)
        if form.is_valid():
            date = form.cleaned_data['date']
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']
            
            if not room.is_available(date, start_time, end_time):
                messages.error(request, 'The selected time slot is not available. Please choose another time.')
                return render(request, 'base/reservation_form.html', {'form': form, 'room': room})
                
            # Form is valid, check room capacity
            participant_count = form.cleaned_data.get('participant_count')
            
            if participant_count > room.capacity:
                messages.error(request, f'The number of participants ({participant_count}) exceeds the room capacity ({room.capacity}).')
                context = {
                    'form': form,
                    'room': room,
                }
                return render(request, 'base/reservation_form.html', context)
                
            # Create the reservation
            reservation = form.save(commit=False)
            reservation.room = room
            reservation.user = request.user
            
            # Extract start_time and end_time from time_slot
            time_slot = form.cleaned_data.get('time_slot')
            if not time_slot and 'time_slot' in initial_data:
                # Use initial time_slot if not in form data
                time_slot = initial_data['time_slot']
                
            start_time_str, end_time_str = time_slot.split('-')
            reservation.start_time = datetime.strptime(start_time_str, '%H:%M').time()
            reservation.end_time = datetime.strptime(end_time_str, '%H:%M').time()
            
            # Save the reservation to the database
            reservation.save()
            print("========= SENDING MEETING CREATION NOTIFICATION =========")
            print(f"Reservation created: {reservation.id} - {reservation.title}")
            participants = reservation.get_participant_list()
            if participants:
                print(f"Sending notification to {len(participants)} participants: {', '.join(participants)}")
                
                subject = f"📅 Meeting Invite: {reservation.title}"
                message = f"""
                Hi there!

                You're invited to an upcoming meeting:

                🗓️ **{reservation.title}**
                📍 {reservation.room.name}
                📆 {reservation.date}
                ⏰ {reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}

                💡 **What's it about:**
                {reservation.description}

                We look forward to seeing you there!
                Please add this to your calendar.
                [View Details](http://localhost:8000)
                """
                
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=participants,
                        fail_silently=False,
                    )
                    print(f"Notification emails sent successfully!")
                    
                    # چون ایمیل ارسال شده، reservation.reminder_sent را true کنید
                    # تا در ارسال زمانبندی شده دوباره ارسال نشود
                    reservation.reminder_sent = True
                    reservation.save(update_fields=['reminder_sent'])
                    
                except Exception as e:
                    print(f"ERROR sending notification emails: {str(e)}")
            else:
                print("No participant emails specified. No notifications sent.")
            
            # نمایش پیام موفقیت و ریدایرکت
            messages.success(request, 'Reservation created successfully and notifications sent!')
            return redirect('room-detail', pk=room.id)

            # Show success message and redirect
            #messages.success(request, 'Reservation created successfully!')
            #return redirect('room-detail', pk=room.id)
        else:
            # Form is invalid, print errors for debugging
            print(f"Form errors: {form.errors}")
            messages.error(request, 'There was an error with your reservation. Please check the form.')
    else:
        form = ReservationForm(initial=initial_data)
    
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
def cancel_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Check if the user is authorized to cancel this reservation
    if request.user != reservation.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to cancel this reservation.")
        return redirect('home')
    
    if request.method == 'POST':
        reservation.delete()
        messages.success(request, 'Reservation cancelled successfully!')
        
        # Redirect based on user type
        if request.user.is_staff:
            return redirect('admin-reservations')
        else:
            return redirect('user-reservations')
    
    context = {
        'obj': reservation,
        'type': 'reservation'
    }
    
    return render(request, 'base/delete.html', context)

# Admin Views
@login_required
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

@login_required
@staff_member_required
def admin_reservations(request):
    reservations_list = Reservation.objects.all().order_by('-date', 'start_time')
    
    # Pagination
    paginator = Paginator(reservations_list, 10)  # Show 10 reservations per page
    page = request.GET.get('page')
    
    try:
        reservations = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        reservations = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        reservations = paginator.page(paginator.num_pages)
    
    context = {
        'reservations': reservations,
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
# Email reminder function (to be scheduled with a task scheduler like Celery)
def send_reservation_reminders():
    """Send email reminders for upcoming reservations"""
    print("========= STARTING EMAIL REMINDER PROCESS =========")
    print(f"Current time: {datetime.now()}")
    
    # Get reservations for tomorrow
    tomorrow = datetime.now().date() + timedelta(days=1)
    print(f"Looking for reservations on: {tomorrow}")
    
    upcoming_reservations = Reservation.objects.filter(
        date=tomorrow,
        reminder_sent=False
    )
    
    print(f"Found {upcoming_reservations.count()} reservations that need reminders")
    
    for reservation in upcoming_reservations:
        print(f"\nProcessing reservation: {reservation.id} - {reservation.title}")
        print(f"Room: {reservation.room.name}")
        print(f"Time: {reservation.start_time} - {reservation.end_time}")
        
        participants = reservation.get_participant_list()
        print(f"Participant emails extracted: {len(participants)}")
        if participants:
            print(f"Sending emails to: {', '.join(participants)}")
            
            subject = f"Reminder: Meeting in {reservation.room.name} tomorrow"
            message = f"""
            Hello ,This is a reminder that you have a meeting scheduled for tomorrow:
            
            Title: {reservation.title}
            Room: {reservation.room.name}
            Date: {reservation.date}
            Time: {reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}
            
            Description:
            {reservation.description}
            
            Please be on time.
            http://localhost:8000
            """
            
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=participants,
                    fail_silently=False,
                )
                print(f"Email sent successfully!")
                
                # Mark as sent
                reservation.reminder_sent = True
                reservation.save()
                print(f"Reservation {reservation.id} marked as reminded")
            except Exception as e:
                print(f"ERROR sending email: {str(e)}")
        else:
            print("No participant emails found, skipping this reservation")
    
    print("\n========= EMAIL REMINDER PROCESS COMPLETED =========")
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


def about(request):
    return render(request, 'base/about.html')

@login_required
def join_meet(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    current_status = room.get_current_status()
    if current_status['status'] != 'occupied':
        messages.error(request, 'This room is not currently in use.')
        return redirect('room-detail', pk=room.id)
    
    active_reservation = current_status['reservation']
    user_email = request.user.email
    participant_emails = active_reservation.get_participant_list()

    if request.user == active_reservation.user or user_email in participant_emails:
        context = {
            'room': room,
            'reservation': active_reservation,
            'welcome_message': 'Welcome to the meeting',
        }
        return render(request, 'base/meeting_room.html', context)
    else:
        messages.error(request, 'You are not authorized to join this meeting.')
        return redirect('room-detail', pk=room.id)


async def meeting_room(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    room = reservation.room
    
    context = {
        'reservation': reservation,
        'room': room,
        'welcome_message': f'Welcome to {room.name}'
    }
    return render(request, 'base/meeting_room.html', context)

async def whiteboard_update(request):
    if request.method == "POST":
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"whiteboard_{request.POST.get('room_id')}", 
            {
                "type": "whiteboard.update",
                "data": request.POST.get('data')
            }
        )
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)
# End !