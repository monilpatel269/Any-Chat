from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.serializers import serialize
from django.utils import timezone
from django.core.paginator import Paginator
import json
import asyncio

from chat.models import RoomChatMessage, PrivateChatRoom, UnreadChatRoomMessages
from friend.models import FriendList
from account.utils import LazyAccountEncoder
from chat.utils import calculate_timestamp, LazyRoomChatMessageEncoder
from chat.exceptions import ClientError
from chat.constants import *
from account.models import Account


class ChatConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):

        await self.accept()
        self.room_id = None

    async def receive_json(self, content):
        command = content.get("command", None)
        try:
            if command == "join":
                await self.join_room(content["room"])
            elif command == "leave":
                await self.leave_room(content["room"])
            elif command == "send":
                if len(content["message"].lstrip()) == 0:
                    raise ClientError(422, "You can't send an empty message.")
                await self.send_room(content["room_id"], content["message"])
            elif command == "get_room_chat_messages":
                await self.display_progress_bar(True)
                room = await get_room_or_error(content["room_id"], self.scope["user"])
                payload = await get_room_chat_messages(room, content["page_number"])
                if payload != None:
                    payload = json.loads(payload)
                    await self.send_messages_payload(
                        payload["messages"], payload["new_page_number"]
                    )
                else:
                    raise ClientError(
                        204, "Something went wrong retriveving the chatroom messages."
                    )

                await self.display_progress_bar(False)
            elif command == "get_user_info":
                await self.display_progress_bar(True)
                room = await get_room_or_error(content["room_id"], self.scope["user"])
                payload = await get_user_info(room, self.scope["user"])
                if payload != None:
                    payload = json.loads(payload)
                    await self.send_user_info_payload(payload["user_info"])
                else:
                    raise ClientError(
                        204,
                        "Something went wrong retreiving the order users account details.",
                    )
                await self.display_progress_bar(False)
        except ClientError as e:
            await self.handle_client_error(e)

    async def disconnect(self, code):
        try:
            if self.room_id != None:
                await self.leave_room(self.room_id)
        except Exception as e:
            pass

    async def join_room(self, room_id):
        try:
            room = await get_room_or_error(room_id, self.scope["user"])
        except ClientError as e:
            return await self.handle_client_error(e)

        await connect_user(room, self.scope["user"])

        self.room_id = room.id

        await on_user_connected(room, self.scope["user"])

        await self.channel_layer.group_add(
            room.group_name,
            self.channel_name,
        )

        await self.send_json(
            {
                "join": str(room.id),
            }
        )

        if self.scope["user"].is_authenticated:
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "chat.join",
                    "room_id": room_id,
                    "profile_image": self.scope["user"].profile_image.url,
                    "username": self.scope["user"].username,
                    "user_id": self.scope["user"].id,
                },
            )

    async def leave_room(self, room_id):
        room = await get_room_or_error(room_id, self.scope["user"])

        await disconnect_user(room, self.scope["user"])
        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "chat.leave",
                "room_id": room_id,
                "profile_image": self.scope["user"].profile_image.url,
                "username": self.scope["user"].username,
                "user_id": self.scope["user"].id,
            },
        )

        self.room_id = None
        await self.channel_layer.group_discard(
            room.group_name,
            self.channel_name,
        )
        await self.send_json(
            {
                "leave": str(room.id),
            }
        )

    async def send_room(self, room_id, message):
        if self.room_id != None:
            if str(room_id) != str(self.room_id):
                raise ClientError("ROOM_ACCESS_DENIED", "Room access denied")
        else:
            raise ClientError("ROOM_ACCESS_DENIED", "Room access denied")

        room = await get_room_or_error(room_id, self.scope["user"])
        connected_users = room.connected_user.all()

        await asyncio.gather(
            *[
                append_unread_msg_if_not_connected(
                    room, room.user1, connected_users, message
                ),
                append_unread_msg_if_not_connected(
                    room, room.user2, connected_users, message
                ),
                create_room_chat_message(room, self.scope["user"], message),
            ]
        )

        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "chat.message",
                "profile_image": self.scope["user"].profile_image.url,
                "username": self.scope["user"].username,
                "user_id": self.scope["user"].id,
                "message": message,
            },
        )

    async def chat_join(self, event):
        if event["username"]:
            await self.send_json(
                {
                    "msg_type": MSG_TYPE_ENTER,
                    "room": event["room_id"],
                    "profile_image": event["profile_image"],
                    "username": event["username"],
                    "user_id": event["user_id"],
                    "message": event["username"] + " connected.",
                }
            )

    async def chat_leave(self, event):
        if event["username"]:
            await self.send_json(
                {
                    "msg_type": MSG_TYPE_LEAVE,
                    "room": event["room_id"],
                    "profile_image": event["profile_image"],
                    "username": event["username"],
                    "user_id": event["user_id"],
                    "message": event["username"] + " disconnected.",
                }
            )

    async def chat_message(self, event):
        timestamp = calculate_timestamp(timezone.now())

        await self.send_json(
            {
                "msg_type": MSG_TYPE_MESSAGE,
                "profile_image": event["profile_image"],
                "username": event["username"],
                "user_id": event["user_id"],
                "message": event["message"],
                "natural_timestamp": timestamp,
            }
        )
    
    async def send_messages_payload(self, messages, new_page_number):
        """
        Send a payload of messages to the ui
        """

        await self.send_json(
            {
                "messages_payload": "messages_payload",
                "messages": messages,
                "new_page_number": new_page_number,
            },
        )

    async def send_message_payload(self, messages, new_page_number):
        await self.send_json(
            {
                "message_payload": "message_payload",
                "messages": messages,
                "new_page_number": new_page_number,
            }
        )

    async def send_user_info_payload(self, user_info):
        await self.send_json(
            {
                "user_info": user_info,
            }
        )

    async def display_progress_bar(self, is_displayed):
        await self.send_json(
            {
                "display_progress_bar": is_displayed,
            }
        )

    async def handle_client_error(self, e):
        errorData = {}
        errorData["error"] = e.code
        if e.message:
            errorData["message"] = e.message
            await self.send_json(errorData)

        return

@database_sync_to_async
def get_room_or_error(room_id,user):
    try:
        room = PrivateChatRoom.objects.get(id=room_id)
    except PrivateChatRoom.DoesNotExist:
        raise ClientError("ROOM_INVALID", "Invalid room.")
    
    if user != room.user1 and user != room.user2:
        raise ClientError("ROOM_ACCESS_DENIED", "You do not have permission to join this room.")
    
    friend_list = FriendList.objects.get(user=user).friends.all()

    if room.user1 not in friend_list:
        if room.user2 not in friend_list:
            raise ClientError("ROOM_ACCES_DENIED", "You must be friends to chat.")
    
    return room

@database_sync_to_async
def get_user_info(room, user):
    try:
        other_user = room.user1
        if other_user == user:
            other_user = room.user2
        
        payload = {}
        s = LazyAccountEncoder()
        payload["user_info"] = s.serialize([other_user])[0]
        return json.dumps(payload)
    
    except ClientError as e:
        raise ClientError("DATA_ERROR","Unable to get that users information.")

@database_sync_to_async
def create_room_chat_message(room, user, message):
    return RoomChatMessage.objects.create(user=user, room=room, content=message)

@database_sync_to_async
def get_room_chat_messages(room, page_number):
    try:
        qs = RoomChatMessage.objects.by_room(room)
        p = Paginator(qs, DEFAULT_ROOM_CHAT_MESSAGE_PAGE_SIZE)

        payload = {}
        messages_data = None
        new_page_number = int(page_number)
        if new_page_number <= p.num_pages:
            new_page_number += 1
            s = LazyRoomChatMessageEncoder()
            payload["messages"] = s.serialize(p.page(page_number).object_list)
        else:
            payload["messages"] = "None"
        payload["new_page_number"] = new_page_number
        return json.dumps(payload)

    except Exception as e:
    
    return None

@database_sync_to_async
def connect_user(room, user):
    account = Account.objects.get(id=user.id)
    return room.connect_user(account)

@database_sync_to_async
def disconnect_user(room, user):
    account = Account.objects.get(id=user.id)
    return room.disconnect_user(account)

@database_sync_to_async
def append_unread_msg_if_not_connected(room,user,connected_user,message):
    if not user in connected_user:
        try:
            unread_msgs = UnreadChatRoomMessages.objects.get(room=room, user=user)
            unread_msgs.most_recent_message = message
            unread_msgs.count += 1
            unread_msgs.save()
        
        except UnreadChatRoomMessages.DoesNotExist:
            UnreadChatRoomMessages(room=room, user=user, count=1).save()
            pass
    return

@database_sync_to_async
def on_user_connected(room, user):
    connected_user = room.connected_user.all()
    if user in connected_user:
        try:
            unread_msgs = UnreadChatRoomMessages.objects.get(room=room, user=user)
            unread_msgs.count = 0
            unread_msgs.save()
        except UnreadChatRoomMessages.DoesNotExist:
            UnreadChatRoomMessages(room=room, user=user).save()
            pass
    return