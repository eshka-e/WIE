from django.contrib import admin
from .models import (
    Profile, Impulse, Comment, Resonance, Landmark,
    Notification, Space, Warning, UserQuestion, Report
)
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

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



@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ('get_name_display', 'order')
    list_editable = ('order',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'impulse', 'created_at', 'deleted_by_moderator')
    list_filter = ('created_at',)
    search_fields = ('content', 'author__user__username')
    actions = ['delete_selected_with_notification']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author__user')

    def delete_selected_with_notification(self, request, queryset):
        moderator = request.user.profile
        for comment in queryset:
            # Создаём уведомление автору комментария
            Notification.objects.create(
                recipient=comment.author,
                sender=moderator,
                notification_type='moderation',
                impulse=comment.impulse,
                comment=comment,
                metadata={
                    'action': 'delete',
                    'reason': 'Комментарий удалён модератором',
                    'content_preview': comment.content[:100]
                }
            )
            # Удаляем комментарий
            comment.delete()
        self.message_user(request, f'Удалено {queryset.count()} комментариев с отправкой уведомлений')

    delete_selected_with_notification.short_description = 'Удалить выбранные комментарии с уведомлением'

    # Переопределяем стандартное удаление через кнопку "Удалить"
    def delete_model(self, request, obj):
        # Создаём уведомление перед удалением
        Notification.objects.create(
            recipient=obj.author,
            sender=request.user.profile,
            notification_type='moderation',
            impulse=obj.impulse,
            comment=obj,
            metadata={
                'action': 'delete',
                'reason': 'Комментарий удалён модератором',
                'content_preview': obj.content[:100]
            }
        )
        obj.delete()
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

# ========== НОВЫЕ МОДЕЛИ ==========

@admin.register(Warning)
class WarningAdmin(admin.ModelAdmin):
    list_display = ('user', 'moderator', 'reason', 'created_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Новое предупреждение
            # Отправляем уведомление пользователю
            Notification.objects.create(
                recipient=obj.user,
                sender=request.user.profile,
                notification_type='moderation',
                metadata={
                    'action': 'warning',
                    'reason': obj.reason,
                    'warnings_count': Warning.objects.filter(user=obj.user, is_active=True).count() + 1
                }
            )
        super().save_model(request, obj, form, change)

@admin.register(UserQuestion)
class UserQuestionAdmin(admin.ModelAdmin):
    list_display = ('email', 'topic', 'question', 'status', 'created_at')
    list_filter = ('topic', 'status', 'created_at')
    search_fields = ('email', 'question', 'context')
    readonly_fields = ('created_at',)

    def save_model(self, request, obj, form, change):
        # Если ответ был изменён и статус стал 'answered'
        if change and 'answer' in form.changed_data and obj.answer:
            obj.status = 'answered'
            obj.answered_at = timezone.now()

            # Отправляем письмо пользователю
            send_mail(
                subject=f'Ответ на ваш вопрос | WHOisE',
                message=f'Здравствуйте!\n\nВы спрашивали:\n"{obj.question}"\n\nОтвет администратора:\n{obj.answer}\n\nС уважением, команда WHOisE',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[obj.email],
                fail_silently=False,
            )

        super().save_model(request, obj, form, change)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported_impulse', 'reason', 'status', 'created_at')
    list_filter = ('reason', 'status', 'created_at')
    search_fields = ('reporter__user__username', 'description')
    raw_id_fields = ('reporter', 'reported_impulse', 'reported_comment')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Информация о жалобе', {
            'fields': ('reporter', 'reason', 'description')
        }),
        ('Объект жалобы', {
            'fields': ('reported_impulse', 'reported_comment')
        }),
        ('Статус', {
            'fields': ('status',)
        }),
    )