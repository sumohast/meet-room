from django.test import TestCase

# Create your tests here.
# this file check a some method and view 

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail
from datetime import date, time, datetime, timedelta
from .models import Room, Reservation, ChatMessage
from .forms import ReservationForm, UserCreateForm
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from .consumers import ChatConsumer
import json

class RoomModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.room = Room.objects.create(name="Test Room", capacity=10)

    def test_room_availability(self):
        """Test Room.is_available method"""
        # Test when room is available
        is_available = self.room.is_available(date(2025, 5, 24), time(10, 0), time(11, 0))
        self.assertTrue(is_available)

        # Create a conflicting reservation
        Reservation.objects.create(
            room=self.room,
            user=self.user,
            title="Test Reservation",
            date=date(2025, 5, 24),
            start_time=time(10, 0),
            end_time=time(11, 0),
            participant_count=5
        )
        is_available = self.room.is_available(date(2025, 5, 24), time(10, 0), time(11, 0))
        self.assertFalse(is_available)

    def test_get_current_status(self):
        """Test Room.get_current_status method"""
        now = datetime.now()
        today = now.date()
        current_time = now.time()

        # Test when room is free
        status = self.room.get_current_status()
        self.assertEqual(status['status'], 'free')

        # Create an active reservation
        reservation = Reservation.objects.create(
            room=self.room,
            user=self.user,
            title="Active Reservation",
            date=today,
            start_time=(now - timedelta(minutes=30)).time(),
            end_time=(now + timedelta(minutes=30)).time(),
            participant_count=5
        )
        status = self.room.get_current_status()
        self.assertEqual(status['status'], 'occupied')
        self.assertEqual(status['reservation'], reservation)

    def test_get_available_time_slots(self):
        """Test Room.get_available_time_slots method"""
        today = date(2025, 5, 24)
        # Create a reservation
        Reservation.objects.create(
            room=self.room,
            user=self.user,
            title="Test Reservation",
            date=today,
            start_time=time(10, 0),
            end_time=time(11, 0),
            participant_count=5
        )
        slots = self.room.get_available_time_slots(today)
        # Check that 10:00-11:00 is not in available slots
        self.assertNotIn((time(10, 0), time(11, 0)), slots)
        # Check that 11:00-12:00 is available
        self.assertIn((time(11, 0), time(12, 0)), slots)

class ReservationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.room = Room.objects.create(name="Test Room", capacity=10)
        self.reservation = Reservation.objects.create(
            room=self.room,
            user=self.user,
            title="Test Reservation",
            date=date(2025, 5, 24),
            start_time=time(10, 0),
            end_time=time(11, 0),
            participant_count=5,
            participants_emails="user1@example.com, user2@example.com"
        )

    def test_get_participant_list(self):
        """Test Reservation.get_participant_list method"""
        emails = self.reservation.get_participant_list()
        self.assertEqual(emails, ['user1@example.com', 'user2@example.com'])

    def test_is_active(self):
        """Test Reservation.is_active method"""
        now = datetime.now()
        today = now.date()
        reservation = Reservation.objects.create(
            room=self.room,
            user=self.user,
            title="Active Reservation",
            date=today,
            start_time=(now - timedelta(minutes=30)).time(),
            end_time=(now + timedelta(minutes=30)).time(),
            participant_count=5
        )
        self.assertTrue(reservation.is_active())

        # Test inactive reservation
        past_reservation = Reservation.objects.create(
            room=self.room,
            user=self.user,
            title="Past Reservation",
            date=today - timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            participant_count=5
        )
        self.assertFalse(past_reservation.is_active())

class ReservationFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.room = Room.objects.create(name="Test Room", capacity=10)

    def test_valid_reservation(self):
        """Test valid reservation form submission"""
        form_data = {
            'title': 'Test Meeting',
            'description': 'Test Description',
            'date': '2025-05-24',
            'time_slot': '10:00-11:00',
            'participant_count': 5,
            'participants_emails': 'user1@example.com, user2@example.com'
        }
        form = ReservationForm(data=form_data, initial={'room': self.room})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['start_time'], time(10, 0))
        self.assertEqual(form.cleaned_data['end_time'], time(11, 0))

    def test_exceed_capacity(self):
        """Test form validation for exceeding room capacity"""
        form_data = {
            'title': 'Test Meeting',
            'description': 'Test Description',
            'date': '2025-05-24',
            'time_slot': '10:00-11:00',
            'participant_count': 15,  # Exceeds capacity
            'participants_emails': 'user1@example.com'
        }
        form = ReservationForm(data=form_data, initial={'room': self.room})
        self.assertFalse(form.is_valid())
        self.assertIn('The number of participants (15) exceeds the room capacity (10).', str(form.errors))

    def test_past_reservation(self):
        """Test form validation for past reservations"""
        yesterday = (datetime.now() - timedelta(days=1)).date()
        form_data = {
            'title': 'Test Meeting',
            'description': 'Test Description',
            'date': yesterday.isoformat(),
            'time_slot': '10:00-11:00',
            'participant_count': 5
        }
        form = ReservationForm(data=form_data, initial={'room': self.room})
        self.assertFalse(form.is_valid())
        self.assertIn('Cannot make reservations in the past', str(form.errors))

class UserCreateFormTests(TestCase):
    def test_valid_user_creation(self):
        """Test valid user creation form"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123'
        }
        form = UserCreateForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_password_mismatch(self):
        """Test user creation with mismatched passwords"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'testpass123',
            'password2': 'differentpass'
        }
        form = UserCreateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.room = Room.objects.create(name="Test Room", capacity=10)

    def test_home_view(self):
        """Test home view displays rooms"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Room")

    def test_create_reservation_authenticated(self):
        """Test creating a reservation when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'title': 'Test Meeting',
            'description': 'Test Description',
            'date': '2025-05-24',
            'time_slot': '10:00-11:00',
            'participant_count': 5,
            'participants_emails': 'user1@example.com'
        }
        response = self.client.post(reverse('create-reservation', kwargs={'room_id': self.room.id}), form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Reservation.objects.filter(title='Test Meeting').exists())

    def test_create_reservation_unauthenticated(self):
        """Test create reservation redirects to login for unauthenticated users"""
        response = self.client.get(reverse('create-reservation', kwargs={'room_id': self.room.id}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_cancel_reservation(self):
        """Test canceling a reservation"""
        self.client.login(username='testuser', password='testpass123')
        reservation = Reservation.objects.create(
            room=self.room,
            user=self.user,
            title="Test Reservation",
            date=date(2025, 5, 24),
            start_time=time(10, 0),
            end_time=time(11, 0),
            participant_count=5
        )
        response = self.client.post(reverse('cancel-reservation', kwargs={'reservation_id': reservation.id}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Reservation.objects.filter(id=reservation.id).exists())

    def test_forgot_password(self):
        """Test forgot password sends email"""
        response = self.client.post(reverse('forgot-password'), {'email': 'test@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Password Reset Request', mail.outbox[0].subject)

class ChatConsumerTests(TestCase):
    async def test_chat_message(self):
        """Test sending and receiving chat messages"""
        user = await database_sync_to_async(User.objects.create_user)(
            username='testuser', password='testpass123'
        )
        room = await database_sync_to_async(Room.objects.create)(name="Test Room", capacity=10)
        reservation = await database_sync_to_async(Reservation.objects.create)(
            room=room,
            user=user,
            title="Test Reservation",
            date=date(2025, 5, 24),
            start_time=time(10, 0),
            end_time=time(11, 0),
            participant_count=5
        )

        # Create communicator
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{reservation.id}/")
        communicator.scope['user'] = user
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send a message
        await communicator.send_json_to({
            'type': 'chat_message',
            'message': 'Hello, world!'
        })

        # Receive the message
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'chat_message')
        self.assertEqual(response['message'], 'Hello, world!')
        self.assertEqual(response['username'], 'testuser')

        # Check if message is saved in database
        message_exists = await database_sync_to_async(ChatMessage.objects.filter)(
            reservation=reservation,
            user=user,
            message='Hello, world!'
        ).exists()
        self.assertTrue(message_exists)

        await communicator.disconnect()
              