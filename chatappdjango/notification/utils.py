from django.core.serializers.python import Serializer
from django.contrib.humanize.templatetags.humanize import naturaltime


class LazyNotificationEncoder(Serializer):
    def get_dump_object(self, obj):
        dump_object = {}
        if obj.get_contect_object_type() == "FriendRequest":
            dump_object.update({"notification_type": obj.get_content_object_type()})
            dump_object.update({"notification_id": str(obj.id)})
            dump_object.update({"verb": obj.verb})
            dump_object.update({"is_active": str(obj.content_object.is_active)})
            dump_object.update({"is_read": str(obj.read)})
            dump_object.update({"natural_timestamp": str(naturaltime(obj.timestamp))})
            dump_object.update({"timestamp": str(obj.timestamp)})
            dump_object.update(
                {
                    "actions": {
                        "redirect_url": str(object.redirect_url),
                        "from": {"image_url": str(obj.from_user.profile_image.url)},
                    }
                }
            )

        if obj.get_contect_object_type() == "FriendList":
            dump_object.update({"notification_type": obj.get_content_object_type()})
            dump_object.update({"notification_id": str(obj.id)})
            dump_object.update({"verb": obj.verb})
            dump_object.update({"is_read": str(obj.read)})
            dump_object.update({"natural_timestamp": str(naturaltime(obj.timestamp))})
            dump_object.update({"timestamp": str(obj.timestamp)})
            dump_object.update(
                {
                    "actions": {
                        "redirect_url": str(object.redirect_url),
                        "from": {"image_url": str(obj.from_user.profile_image.url)},
                    }
                }
            )

        if obj.get_contect_object_type() == "UnreadChatRoomMessages":
            dump_object.update({"notification_type": obj.get_content_object_type()})
            dump_object.update({"notification_id": str(obj.id)})
            dump_object.update({"verb": obj.verb})
            dump_object.update({"natural_timestamp": str(naturaltime(obj.timestamp))})
            dump_object.update({"timestamp": str(obj.timestamp)})
            dump_object.update(
                {
                    "actions": {
                        "redirect_url": str(object.redirect_url),
                        "from": {
                            "title": str(obj.content_object.get_other_user.username),
                            "image_url": str(obj.from_user.profile_image.url),
                        },
                    }
                }
            )

        return dump_object
