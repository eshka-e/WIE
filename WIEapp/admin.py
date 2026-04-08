from django.contrib import admin
from .models import Profile, Impulse, Tag, Comment, Resonance, Landmark, Notification, Space

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('created_at',)

@admin.register(Impulse)
class ImpulseAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'space', 'created_at')
    list_filter = ('space', 'created_at')
    search_fields = ('title', 'content')
    filter_horizontal = ('tags',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ('get_name_display', 'order')
    list_editable = ('order',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'impulse', 'created_at')
    list_filter = ('created_at',)

@admin.register(Resonance)
class ResonanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'impulse', 'resonance_type', 'created_at')
    list_filter = ('resonance_type', 'created_at')

@admin.register(Landmark)
class LandmarkAdmin(admin.ModelAdmin):
    list_display = ('follower', 'target_type', 'target_id', 'created_at')
    list_filter = ('target_type',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'sender', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')