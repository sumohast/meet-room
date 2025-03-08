from django.shortcuts import render , redirect
from django.http import HttpResponse
from .models import Room , Topic , Message
from .forms import RoomForm
from django.contrib import messages
# Create your views here.

#rooms = [
#    {'id':1 , 'name':'Lets learn python!'} ,
#    {'id':2 , 'name':'Lets learn node js!'} , 
#    {'id':3 , 'name':'Lets learn frontend!'}
#]

def home(request):
    rooms = Room.objects.all()
    topic = Topic.objects.all()

    context = {'rooms':rooms, 'topics':topic}
    return render(request, 'base/home.html', context)

def about(request):
    return HttpResponse('I am a software engineer!')

def room(request, pk):
    room = Room.objects.get(id=pk)
    room_messages = room.message_set.all()
    participants = room.participants.all()

    if request.method == 'POST':
        message = Message.objects.create(
            user=request.user,
            room=room,
            body=request.POST.get('body')
        )
        room.participants.add(request.user)
        return redirect('room', pk=room.id)

    context = {'room': room, 'room_messages': room_messages,
               'participants': participants}
    return render(request, 'base/room.html', context)



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
        return redirect('home')

    context = {'form': form, 'topics': topics}
    return render(request, 'base/room_form.html', context)



def updateRoom(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)
    topics = Topic.objects.all()
    if request.user != room.host:
        return HttpResponse('Your are not allowed here!!')

    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)
        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()
        return redirect('home')

    context = {'form': form, 'topics': topics, 'room': room}
    return render(request, 'base/room_form.html', context)

def deleteRoom(request, pk):
    room = Room.objects.get(id=pk)
    return render(request , 'delete.html' , {'obj':room})