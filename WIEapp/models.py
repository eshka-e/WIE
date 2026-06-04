from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='аватар')
    banner = models.ImageField(upload_to='covers/', blank=True, null=True, verbose_name='баннер')
    bio = models.TextField(max_length=500, blank=True, verbose_name='о себе')
    display_name = models.CharField(max_length=100, blank=True, verbose_name='отображаемое имя')
    is_email_verified = models.BooleanField(default=False, verbose_name='email подтверждён')
    email_verification_token = models.CharField(max_length=100, blank=True, null=True, verbose_name='токен верификации')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='дата регистрации')

    class Meta:
        verbose_name = 'профиль'
        verbose_name_plural = 'профили'

    def __str__(self):
        return f"{self.display_name or self.user.username}"



class Space(models.Model):
    SPACE_TYPES = [
        ('vision', 'ВИДЕНИЕ'),
        ('nerve', 'ЧУТКОСТЬ'),
        ('craft', 'РЕМЕСЛО'),
        ('stream', 'ПОТОК'),
    ]

    name = models.CharField(max_length=20, choices=SPACE_TYPES, unique=True, verbose_name='название')
    description = models.TextField(blank=True, verbose_name='описание')
    order = models.IntegerField(default=0, verbose_name='порядок')

    class Meta:
        ordering = ['order']
        verbose_name = 'пространство'
        verbose_name_plural = 'пространства'

    def __str__(self):
        return self.get_name_display()


class Impulse(models.Model):
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='impulses', verbose_name='автор')
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='impulses', verbose_name='пространство')
    title = models.CharField(max_length=200, verbose_name='заголовок')
    content = models.TextField(verbose_name='содержание')

    image = models.ImageField(upload_to='impulses/images/', blank=True, null=True, verbose_name='изображение')
    video_url = models.URLField(blank=True, null=True, verbose_name='ссылка на видео')
    video_file = models.FileField(upload_to='impulses/videos/', blank=True, null=True, verbose_name='видеофайл')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='дата создания')
    modified_at = models.DateTimeField(auto_now=True, verbose_name='дата изменения')
    is_modified = models.BooleanField(default=False, verbose_name='изменено')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'импульс'
        verbose_name_plural = 'импульсы'

    def __str__(self):
        return f"{self.title} — {self.author.user.username}"


class Comment(models.Model):
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='comments', verbose_name='автор')
    impulse = models.ForeignKey(Impulse, on_delete=models.CASCADE, related_name='comments', verbose_name='импульс')
    content = models.TextField(verbose_name='содержание')
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies',
                                       verbose_name='родительский комментарий')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='дата создания')
    is_modified = models.BooleanField(default=False, verbose_name='изменено')
    deleted_by_moderator = models.BooleanField(default=False, verbose_name='удалён модератором')

    class Meta:
        ordering = ['created_at']
        verbose_name = 'отклик'
        verbose_name_plural = 'отклики'

    def __str__(self):
        return f"Отклик от {self.author.user.username} на {self.impulse.title[:30]}"


class Resonance(models.Model):
    RESONANCE_TYPES = [
        ('heart', 'СЕРДЦЕ'),
        ('blast', 'ВЗРЫВ'),
    ]

    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='resonances', verbose_name='пользователь')
    impulse = models.ForeignKey(Impulse, on_delete=models.CASCADE, related_name='resonances', null=True, blank=True,
                                verbose_name='импульс')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='resonances', null=True, blank=True,
                                verbose_name='комментарий')
    resonance_type = models.CharField(max_length=10, choices=RESONANCE_TYPES, verbose_name='тип резонанса')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='дата создания')

    class Meta:
        unique_together = [
            ('user', 'impulse', 'resonance_type'),
            ('user', 'comment', 'resonance_type'),
        ]
        verbose_name = 'резонанс'
        verbose_name_plural = 'резонансы'

    def __str__(self):
        if self.impulse:
            return f"{self.user.user.username} → {self.get_resonance_type_display()} → {self.impulse.title[:30]}"
        else:
            return f"{self.user.user.username} → {self.get_resonance_type_display()} → комментарий"


class Landmark(models.Model):
    TARGET_TYPES = [
        ('profile', 'ПРОФИЛЬ'),
        ('space', 'ПРОСТРАНСТВО'),
    ]

    follower = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='landmarks', verbose_name='подписчик')
    target_type = models.CharField(max_length=20, choices=TARGET_TYPES, verbose_name='тип цели')
    target_id = models.PositiveIntegerField(verbose_name='ID цели')
    is_muted = models.BooleanField(default=False, verbose_name='заглушен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='дата создания')

    class Meta:
        unique_together = ['follower', 'target_type', 'target_id']
        verbose_name = 'ориентир'
        verbose_name_plural = 'ориентиры'

    def __str__(self):
        return f"{self.follower.user.username} → ориентир #{self.target_id}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('comment', 'НОВЫЙ ОТКЛИК'),
        ('reply', 'ОТВЕТ НА ОТКЛИК'),
        ('resonance', 'РЕЗОНАНС'),
        ('landmark', 'НОВЫЙ ОРИЕНТИР'),
        ('moderation', 'МОДЕРАЦИЯ'),
    ]

    recipient = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='notifications',
                                  verbose_name='получатель')
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='sent_notifications',
                               verbose_name='отправитель')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name='тип уведомления')
    impulse = models.ForeignKey(Impulse, on_delete=models.CASCADE, null=True, blank=True, verbose_name='импульс')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, verbose_name='комментарий')
    is_read = models.BooleanField(default=False, verbose_name='прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='дата создания')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='дополнительные данные')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'уведомление'
        verbose_name_plural = 'уведомления'

    def __str__(self):
        return f"{self.recipient.user.username} — {self.get_notification_type_display()}"


class Report(models.Model):
    REASON_CHOICES = [
        ('spam', 'Спам'),
        ('harassment', 'Оскорбления / домогательства'),
        ('illegal', 'Незаконный контент'),
        ('offtopic', 'Не по теме'),
        ('other', 'Другое'),
    ]

    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('reviewed', 'Рассмотрено'),
        ('rejected', 'Отклонено'),
    ]

    reporter = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='reports_made',
                                 verbose_name='пожаловавшийся')
    reported_user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='reports_received', null=True,
                                      blank=True, verbose_name='пользователь')
    reported_impulse = models.ForeignKey(Impulse, on_delete=models.CASCADE, null=True, blank=True,
                                         verbose_name='импульс')
    reported_comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True,
                                         verbose_name='комментарий')
    reason = models.CharField(max_length=50, choices=REASON_CHOICES, verbose_name='причина')
    description = models.TextField(blank=True, verbose_name='описание')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='дата создания')

    class Meta:
        verbose_name = 'жалоба'
        verbose_name_plural = 'жалобы'

    def __str__(self):
        if self.reported_user:
            return f"Жалоба от {self.reporter.user.username} на {self.reported_user.user.username}"
        elif self.reported_impulse:
            return f"Жалоба от {self.reporter.user.username} на импульс '{self.reported_impulse.title[:30]}'"
        elif self.reported_comment:
            return f"Жалоба от {self.reporter.user.username} на комментарий"
        return f"Жалоба #{self.id}"


class Warning(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='warnings', verbose_name='пользователь')
    moderator = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='given_warnings',
                                  verbose_name='модератор')
    reason = models.TextField(default='Нарушение правил платформы', verbose_name='причина')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='дата выдачи')
    is_active = models.BooleanField(default=True, verbose_name='активно')

    class Meta:
        verbose_name = 'предупреждение'
        verbose_name_plural = 'предупреждения'

    def __str__(self):
        return f"Предупреждение {self.user.user.username} от {self.moderator.user.username}"


class UserQuestion(models.Model):
    TOPIC_CHOICES = [
        ('platform', 'О платформе'),
        ('rules', 'Правила и модерация'),
        ('technical', 'Технические проблемы'),
        ('account', 'Аккаунт и профиль'),
        ('other', 'Другое'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Ожидает ответа'),
        ('answered', 'Ответ дан'),
    ]

    user = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, blank=True, verbose_name='пользователь')
    email = models.EmailField(verbose_name='email')
    topic = models.CharField(max_length=20, choices=TOPIC_CHOICES, verbose_name='тема')
    question = models.CharField(max_length=255, verbose_name='вопрос')
    context = models.TextField(blank=True, verbose_name='контекст')
    answer = models.TextField(blank=True, verbose_name='ответ')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='дата создания')
    answered_at = models.DateTimeField(null=True, blank=True, verbose_name='дата ответа')

    class Meta:
        verbose_name = 'вопрос пользователя'
        verbose_name_plural = 'вопросы пользователей'

    def __str__(self):
        return f"Вопрос от {self.email}: {self.question[:50]}"