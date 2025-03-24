from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ChatMessage, Reservation

User = get_user_model()

class WhiteboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'whiteboard_{self.room_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'whiteboard_update',
                'data': data
            }
        )

    async def whiteboard_update(self, event):
        data = event['data']
        await self.send(text_data=json.dumps(data))

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.reservation_id = self.scope['url_route']['kwargs']['reservation_id']
        self.room_group_name = f'chat_{self.reservation_id}'
        
        # اضافه کردن به گروه اتاق
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # ذخیره اطلاعات کاربر
        self.user = self.scope['user']
        
        # پذیرش اتصال
        await self.accept()
        
        # اعلام ورود کاربر به همه
        if self.user.is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_join',
                    'username': self.user.username,
                    'user_id': str(self.user.id)
                }
            )
    
    async def disconnect(self, close_code):
        # اعلام خروج کاربر
        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_leave',
                    'username': self.user.username,
                    'user_id': str(self.user.id)
                }
            )
        
        # خروج از گروه اتاق
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data['message']
            
            # ذخیره پیام در دیتابیس
            if self.user.is_authenticated:
                message_obj = await self.save_message(message)
                
                # ارسال پیام به گروه اتاق
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
        except Exception as e:
            print(f"Error in receive: {e}")
            # ارسال پیام خطا به کاربر
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'An error occurred while processing your message.'
            }))
    
    async def chat_message(self, event):
        # ارسال پیام به WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp']
        }))
    
    async def user_join(self, event):
        # ارسال اطلاعیه ورود کاربر
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'username': event['username'],
            'user_id': event['user_id']
        }))
    
    async def user_leave(self, event):
        # ارسال اطلاعیه خروج کاربر
        await self.send(text_data=json.dumps({
            'type': 'user_leave',
            'username': event['username'],
            'user_id': event['user_id']
        }))
    
    @database_sync_to_async
    def save_message(self, message):
        reservation = Reservation.objects.get(id=self.reservation_id)
        return ChatMessage.objects.create(
            reservation=reservation,
            user=self.user,
            message=message
        )