from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ChatMessage, Reservation

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract reservation ID from URL
        self.reservation_id = self.scope['url_route']['kwargs']['reservation_id']
        
        # Create a unique group name for this reservation
        self.room_group_name = f'chat_{self.reservation_id}'
        
        # Get the current user
        self.user = self.scope["user"]
        
        # Add the channel to the group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept the WebSocket connection
        await self.accept()
        
        # Fetch and send previous messages
        await self.send_previous_messages()
        
        # Notify others that a user has joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'user_id': str(self.user.id),
                'username': self.user.username
            }
        )

    async def disconnect(self, close_code):
        # Notify others that a user has left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_leave',
                'user_id': str(self.user.id),
                'username': self.user.username
            }
        )
        
        # Remove the channel from the group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            
            # Handle different types of messages
            if data.get('type') == 'fetch_messages':
                await self.send_previous_messages()
                return
            
            # Handle chat message
            if 'message' in data:
                message = data['message'].strip()
                if not message:
                    raise ValueError("Empty message")
                
                # Save message to database
                message_obj = await self.save_message(message)
                
                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'username': self.user.username,
                        'user_id': str(self.user.id),
                        'timestamp': message_obj.timestamp.isoformat()
                    }
                )
            
        except json.JSONDecodeError:
            await self.send_error("Invalid message format")
        except ValueError as e:
            await self.send_error(str(e))
        except Exception as e:
            await self.send_error(f"An error occurred: {str(e)}")

    async def send_previous_messages(self):
        """Fetch and send previous messages for the reservation"""
        try:
            # Get the reservation
            reservation = await self.get_reservation()
            
            # Fetch recent messages
            messages = await self.get_messages(reservation)
            
            # Send messages to the client
            await self.send(text_data=json.dumps({
                'type': 'fetch_messages',
                'messages': messages
            }))
        except Exception as e:
            await self.send_error(f"Error fetching messages: {str(e)}")

    async def send_error(self, message):
        """Send an error message to the client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    async def chat_message(self, event):
        """Send a chat message to the WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp']
        }))

    async def user_join(self, event):
        """Send user join notification"""
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'username': event['username'],
            'user_id': event['user_id']
        }))

    async def user_leave(self, event):
        """Send user leave notification"""
        await self.send(text_data=json.dumps({
            'type': 'user_leave',
            'username': event['username'],
            'user_id': event['user_id']
        }))

    @database_sync_to_async
    def save_message(self, message):
        """Save a message to the database"""
        reservation = Reservation.objects.get(id=self.reservation_id)
        return ChatMessage.objects.create(
            reservation=reservation,
            user=self.user,
            message=message
        )

    @database_sync_to_async
    def get_reservation(self):
        """Retrieve the reservation"""
        return Reservation.objects.get(id=self.reservation_id)

    @database_sync_to_async
    def get_messages(self, reservation):
        """Fetch recent messages for the reservation"""
        messages = ChatMessage.objects.filter(
            reservation=reservation
        ).select_related('user').order_by('-timestamp')[:50]
        
        return [{
            'message': message.message,
            'username': message.user.username,
            'userId': str(message.user.id),
            'timestamp': message.timestamp.isoformat()
        } for message in reversed(messages)]  # Reverse to show oldest first
    
    
class WebRTCSignalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.reservation_id = self.scope['url_route']['kwargs']['reservation_id']
        self.room_group_name = f'webrtc_{self.reservation_id}'
        self.user = self.scope["user"]
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others about new connection
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_connected',
                'user_id': str(self.user.id),
                'username': self.user.username
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_disconnected',
                'user_id': str(self.user.id),
                'username': self.user.username
            }
        )
        
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        
        message_type = data.get('type')
        
        if message_type == 'offer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_offer',
                    'offer': data.get('offer'),
                    'sender_id': str(self.user.id),
                    'receiver_id': data.get('receiver_id')
                }
            )
        
        elif message_type == 'answer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_answer',
                    'answer': data.get('answer'),
                    'sender_id': str(self.user.id),
                    'receiver_id': data.get('receiver_id')
                }
            )
        
        elif message_type == 'ice_candidate':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_ice_candidate',
                    'candidate': data.get('candidate'),
                    'sender_id': str(self.user.id),
                    'receiver_id': data.get('receiver_id')
                }
            )

    async def user_connected(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_connected',
            'user_id': event['user_id'],
            'username': event['username']
        }))

    async def user_disconnected(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_disconnected',
            'user_id': event['user_id'],
            'username': event['username']
        }))

    async def webrtc_offer(self, event):
        await self.send(text_data=json.dumps({
            'type': 'offer',
            'offer': event['offer'],
            'sender_id': event['sender_id'],
            'receiver_id': event['receiver_id']
        }))

    async def webrtc_answer(self, event):
        await self.send(text_data=json.dumps({
            'type': 'answer',
            'answer': event['answer'],
            'sender_id': event['sender_id'],
            'receiver_id': event['receiver_id']
        }))

    async def webrtc_ice_candidate(self, event):
        await self.send(text_data=json.dumps({
            'type': 'ice_candidate',
            'candidate': event['candidate'],
            'sender_id': event['sender_id'],
            'receiver_id': event['receiver_id']
        }))