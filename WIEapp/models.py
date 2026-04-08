from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# ПРОФИЛЬ
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    telegram = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"СЛЕД: {self.user.username}"


# ТЕГИ
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# ПРОСТРАНСТВА (РАЗДЕЛЫ)
class Space(models.Model):
    SPACE_TYPES = [
        ('vision', 'ВИДЕНИЕ'),
        ('nerve', 'ЧУТКОСТЬ'),
        ('craft', 'РЕМЕСЛО'),
        ('stream', 'ПОТОК'),
    ]

    name = models.CharField(max_length=20, choices=SPACE_TYPES, unique=True)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.get_name_display()


# ИМПУЛЬСЫ (ПОСТЫ)
class Impulse(models.Model):
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='impulses')
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='impulses')
    title = models.CharField(max_length=200)
    content = models.TextField()
    tags = models.ManyToManyField(Tag, related_name='impulses', blank=True)

    # Медиа (в зависимости от пространства)
    image = models.ImageField(upload_to='impulses/images/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_modified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} — {self.author.user.username}"


# ОТКЛИКИ (КОММЕНТАРИИ)
class Comment(models.Model):
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='comments')
    impulse = models.ForeignKey(Impulse, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Отклик от {self.author.user.username}"


# РЕЗОНАНСЫ (РЕАКЦИИ)
class Resonance(models.Model):
    RESONANCE_TYPES = [
        ('heart', 'СЕРДЦЕ'),
        ('blast', 'ВЗРЫВ'),
    ]

    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='resonances')
    impulse = models.ForeignKey('Impulse', on_delete=models.CASCADE, related_name='resonances', null=True, blank=True)
    comment = models.ForeignKey('Comment', on_delete=models.CASCADE, related_name='resonances', null=True, blank=True)
    resonance_type = models.CharField(max_length=10, choices=RESONANCE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Исправленный unique_together
        unique_together = [
            ('user', 'impulse', 'resonance_type'),
            ('user', 'comment', 'resonance_type'),
        ]

    def __str__(self):
        target = self.impulse if self.impulse else self.comment
        return f"{self.user.user.username} → {self.get_resonance_type_display()} → {target}"

# ОРИЕНТИРЫ (ПОДПИСКИ)
class Landmark(models.Model):
    TARGET_TYPES = [
        ('profile', 'СЛЕД'),
        ('space', 'ПРОСТРАНСТВО'),
    ]

    follower = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='landmarks')
    target_type = models.CharField(max_length=20, choices=TARGET_TYPES)
    target_id = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['follower', 'target_type', 'target_id']

    def __str__(self):
        return f"{self.follower.user.username} → {self.target_type}#{self.target_id}"


# СИГНАЛЫ
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('comment', 'НОВЫЙ ОТКЛИК'),
        ('reply', 'ОТВЕТ НА ОТКЛИК'),
        ('resonance', 'РЕЗОНАНС'),
        ('landmark', 'НОВЫЙ ОРИЕНТИР'),
    ]

    recipient = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    impulse = models.ForeignKey(Impulse, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.user.username} — {self.get_notification_type_display()}"