from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Room, Topic, Message
from .forms import RoomForm, UserCreateForm

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
    
    topics = Topic.objects.all()
    room_count = rooms.count()
    recent_messages = Message.objects.filter(
        Q(room__topic__name__icontains=q)
    )[:5]

    context = {
        'rooms': rooms, 
        'topics': topics, 
        'room_count': room_count,
        'recent_messages': recent_messages,
    }
    return render(request, 'base/home.html', context)

def about(request):
    return render(request, 'base/about.html')

def room(request, pk):
    room = get_object_or_404(Room, id=pk)
    room_messages = room.message_set.all()
    participants = room.participants.all()

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
        'participants': participants , 
    }
    return render(request, 'base/room.html', context)

@login_required
def createRoom(request):
    form = RoomForm()
    topics = Topic.objects.all()
    
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)

        Room.objects.create(
            host=request.user,
            topic=topic,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
        )
        messages.success(request, 'Room created successfully!')
        return redirect('home')

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
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)
        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()
        messages.success(request, 'Room updated successfully!')
        return redirect('home')

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
        
    return render(request, 'base/delete.html', {'obj': room})

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
    
    return render(request, 'base/delete.html', {'obj': message})

def loginPage(request):
    page = 'login'
    
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(username=username)
        except:
            messages.error(request, 'User does not exist')
            
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Username OR password does not exist')
            
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
            messages.error(request, 'An error occurred during registration')
            
    context = {'form': form}
    return render(request, 'base/login_register.html', context)