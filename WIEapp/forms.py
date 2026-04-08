from django import forms
from django.core.exceptions import ValidationError
from .models import Impulse, Comment, Profile, Tag, Space


# ================= ФОРМА ИМПУЛЬСА (С ДИНАМИЧЕСКОЙ ВАЛИДАЦИЕЙ) =================

class ImpulseForm(forms.ModelForm):
    """
    ФОРМА СОЗДАНИЯ/РЕДАКТИРОВАНИЯ ИМПУЛЬСА

    🔄 РЕМАРКИ:
    1. Поле 'tags' — строковое, теги вводятся через запятую.
       При сохранении автоматически создаются или находятся существующие теги.

    2. Валидация медиа в зависимости от пространства:
       - ВИДЕНИЕ (vision): обязательно изображение
       - РЕМЕСЛО (craft): обязательно видео (URL или файл)
       - ЧУТКОСТЬ (nerve): только текст, медиа запрещены
       - ПОТОК (stream): медиа опционально

    3. На фронтенде нужно динамически показывать/скрывать поля
       в зависимости от выбранного space_id.
    """

    tags = forms.CharField(
        max_length=200,
        required=False,
        help_text="Теги через запятую (например: #дизайн, #типографика)",
        widget=forms.TextInput(attrs={
            'placeholder': '#тег1, #тег2, #тег3',
            'class': 'form-input'
        })
    )

    class Meta:
        model = Impulse
        fields = ['space', 'title', 'content', 'image', 'video_url', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'ЗАГОЛОВОК ИМПУЛЬСА',
                'class': 'form-input'
            }),
            'content': forms.Textarea(attrs={
                'rows': 8,
                'placeholder': 'ТЕКСТ ИМПУЛЬСА...',
                'class': 'form-textarea'
            }),
            'space': forms.Select(attrs={
                'class': 'form-select',
                'id': 'space-select'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': 'image/*',
                'id': 'media-image'
            }),
            'video_url': forms.URLInput(attrs={
                'placeholder': 'https://youtu.be/... или https://vimeo.com/...',
                'class': 'form-input',
                'id': 'media-video'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ограничиваем выбор пространств (исключаем ПОТОК? или оставляем)
        self.fields['space'].queryset = Space.objects.all()

        # Для редактирования: предзаполняем поле tags строкой из существующих тегов
        if self.instance and self.instance.pk:
            existing_tags = ', '.join([tag.name for tag in self.instance.tags.all()])
            self.fields['tags'].initial = existing_tags

    def clean(self):
        """
        ВАЛИДАЦИЯ МЕДИА В ЗАВИСИМОСТИ ОТ ПРОСТРАНСТВА
        """
        cleaned_data = super().clean()
        space = cleaned_data.get('space')
        image = cleaned_data.get('image')
        video_url = cleaned_data.get('video_url')

        if not space:
            return cleaned_data

        space_name = space.name

        # ВИДЕНИЕ: обязательно изображение
        if space_name == 'vision':
            if not image and not self.instance.image:
                self.add_error('image', 'Для пространства ВИДЕНИЕ обязательно изображение')
            if video_url:
                self.add_error('video_url', 'В пространстве ВИДЕНИЕ нельзя загружать видео')

        # РЕМЕСЛО: обязательно видео
        elif space_name == 'craft':
            if not video_url and not self.instance.video_url:
                self.add_error('video_url', 'Для пространства РЕМЕСЛО обязательно видео (ссылка на YouTube/Vimeo)')
            if image:
                self.add_error('image', 'В пространстве РЕМЕСЛО нельзя загружать изображения')

        # ЧУТКОСТЬ: только текст, без медиа
        elif space_name == 'nerve':
            if image:
                self.add_error('image', 'В пространстве ЧУТКОСТЬ нельзя загружать изображения')
            if video_url:
                self.add_error('video_url', 'В пространстве ЧУТКОСТЬ нельзя загружать видео')

        # ПОТОК: медиа опционально, можно и то и другое
        elif space_name == 'stream':
            # Никаких ограничений
            pass

        return cleaned_data

    def save(self, commit=True):
        """
        СОХРАНЕНИЕ ИМПУЛЬСА С ОБРАБОТКОЙ ТЕГОВ

        🔄 РЕМАРКА:
        Теги сохраняются после основного сохранения, чтобы была возможность
        работать с ManyToMany полем.
        """
        instance = super().save(commit=False)

        if commit:
            instance.save()
            # Обработка тегов
            tag_string = self.cleaned_data.get('tags', '')
            if tag_string:
                # Очищаем существующие теги
                instance.tags.clear()
                # Разбиваем по запятым, обрезаем пробелы
                tags = [t.strip().lower() for t in tag_string.split(',') if t.strip()]
                for tag_name in tags:
                    # Убираем # если пользователь его ввел
                    if tag_name.startswith('#'):
                        tag_name = tag_name[1:]
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    instance.tags.add(tag)

        return instance


# ================= ФОРМА КОММЕНТАРИЯ (ОТКЛИК) =================

class CommentForm(forms.ModelForm):
    """
    ФОРМА ДЛЯ ОТКЛИКОВ (КОММЕНТАРИЕВ)

    🔄 РЕМАРКА:
    Простая форма, но можно расширить полем для вложенных ответов.
    """

    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'ОСТАВИТЬ ОТКЛИК...',
                'class': 'form-textarea'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].label = ''
        self.fields['content'].required = True


# ================= ФОРМА ПРОФИЛЯ =================

class ProfileForm(forms.ModelForm):
    """
    ФОРМА РЕДАКТИРОВАНИЯ ПРОФИЛЯ СЛЕДА
    """

    class Meta:
        model = Profile
        fields = ['avatar', 'bio', 'telegram']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': 'image/*'
            }),
            'bio': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'РАССКАЖИТЕ О СЕБЕ...\nФОТОГРАФ, ДИЗАЙНЕР, ХОДОВИК. МОЙ БЫТ СВЕТ, ВАШ ТОЖЕ',
                'class': 'form-textarea'
            }),
            'telegram': forms.TextInput(attrs={
                'placeholder': '@username',
                'class': 'form-input'
            })
        }

    def clean_telegram(self):
        telegram = self.cleaned_data.get('telegram', '')
        if telegram and not telegram.startswith('@'):
            telegram = '@' + telegram
        return telegram


# ================= ФОРМА ДЛЯ ОТВЕТА НА КОММЕНТАРИЙ (AJAX) =================

class ReplyForm(forms.Form):
    """
    ФОРМА ДЛЯ ВЛОЖЕННЫХ ОТВЕТОВ (ИСПОЛЬЗУЕТСЯ В AJAX)

    🔄 РЕМАРКА:
    Это простая форма без модели, используется для валидации данных
    перед созданием Comment через AJAX.
    """

    parent_id = forms.IntegerField(required=True)
    content = forms.CharField(max_length=1000, required=True, widget=forms.Textarea)

    def clean_parent_id(self):
        parent_id = self.cleaned_data.get('parent_id')
        try:
            parent_comment = Comment.objects.get(id=parent_id)
        except Comment.DoesNotExist:
            raise ValidationError('Родительский комментарий не найден')
        return parent_id


# ================= ФОРМА ПОИСКА ПО ВОПРОСАМ (ДЛЯ FAQ) =================

class SearchForm(forms.Form):
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'НАЙТИ ВОПРОС...',
            'class': 'form-input search-input'
        })
    )

    space = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Space  # импорт внутри метода, чтобы избежать циклических ссылок
        space_choices = [('all', 'ВСЕ')]
        space_choices += [(s.name, s.get_name_display()) for s in Space.objects.all()]
        self.fields['space'].choices = space_choices

# ================= ФОРМА ЖАЛОБЫ (ДЛЯ МОДЕРАЦИИ) =================

class ReportForm(forms.Form):
    """
    ФОРМА ОТПРАВКИ ЖАЛОБЫ НА ИМПУЛЬС ИЛИ КОММЕНТАРИЙ

    🔄 РЕМАРКА:
    Используется в модальном окне. После отправки создаётся объект Report.
    """

    REASON_CHOICES = [
        ('spam', 'СПАМ'),
        ('harassment', 'ОСКОРБЛЕНИЯ'),
        ('illegal', 'НЕЗАКОННЫЙ КОНТЕНТ'),
        ('offtopic', 'НЕ ПО ТЕМЕ'),
        ('other', 'ДРУГОЕ'),
    ]

    reason = forms.ChoiceField(choices=REASON_CHOICES, widget=forms.RadioSelect)
    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'ПОДРОБНОСТИ (НЕОБЯЗАТЕЛЬНО)...'
        })
    )


# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ФОРМ =================

def get_space_media_requirements(space_name):
    """
    ВОЗВРАЩАЕТ ТРЕБОВАНИЯ К МЕДИА ДЛЯ ПРОСТРАНСТВА
    Используется на фронтенде для динамического отображения подсказок.
    """
    requirements = {
        'vision': {
            'media_required': True,
            'media_type': 'image',
            'help_text': 'Обязательно изображение (JPG, PNG, GIF)'
        },
        'craft': {
            'media_required': True,
            'media_type': 'video',
            'help_text': 'Обязательно видео (ссылка на YouTube или Vimeo)'
        },
        'nerve': {
            'media_required': False,
            'media_type': None,
            'help_text': 'Только текст, изображения и видео запрещены'
        },
        'stream': {
            'media_required': False,
            'media_type': 'optional',
            'help_text': 'Можно добавить изображение или видео (по желанию)'
        }
    }
    return requirements.get(space_name, {})