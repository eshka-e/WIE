# forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm, UserCreationForm
from .models import Impulse, Comment, Profile, Space


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')

    class Meta:
        model = User
        fields = ('email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже зарегистрирован')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']

        base_username = self.cleaned_data['email'].split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user.username = username
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
        return user


class ImpulseForm(forms.ModelForm):
    tags = forms.CharField(max_length=200, required=False, help_text="Теги через запятую")

    class Meta:
        model = Impulse
        fields = ['space', 'title', 'content', 'image', 'video_url']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'ЗАГОЛОВОК ИМПУЛЬСА', 'class': 'form-input'}),
            'content': forms.Textarea(attrs={'rows': 8, 'placeholder': 'ТЕКСТ ИМПУЛЬСА...', 'class': 'form-textarea'}),
            'space': forms.Select(attrs={'class': 'form-select', 'id': 'id_space'}),
            'image': forms.FileInput(attrs={'class': 'form-file', 'accept': 'image/*', 'id': 'media-image'}),
            'video_url': forms.URLInput(
                attrs={'placeholder': 'https://youtu.be/...', 'class': 'form-input', 'id': 'media-video'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Исключаем пространство 'stream' из выбора
        self.fields['space'].queryset = Space.objects.exclude(name='stream')

        # Устанавливаем значение по умолчанию (найди ID пространства 'vision')
        vision_space = Space.objects.filter(name='vision').first()
        if vision_space and not self.instance.pk:  # Только для нового импульса
            self.fields['space'].initial = vision_space.id

        # Делаем поля необязательными по умолчанию
        self.fields['title'].required = False
        self.fields['content'].required = False
        self.fields['image'].required = False
        self.fields['video_url'].required = False
        self.fields['space'].required = True


    def clean(self):
        cleaned_data = super().clean()
        space = cleaned_data.get('space')
        title = cleaned_data.get('title')
        content = cleaned_data.get('content')
        image = cleaned_data.get('image')
        video_url = cleaned_data.get('video_url')

        if not space:
            return cleaned_data

        space_name = space.name

        # ВАЛИДАЦИЯ ДЛЯ ВИДЕНИЕ (vision)
        if space_name == 'vision':
            if not image and not self.instance.image:
                self.add_error('image', 'Для пространства ВИДЕНИЕ обязательно изображение')
            if video_url:
                self.add_error('video_url', 'В пространстве ВИДЕНИЕ нельзя загружать видео')

        # ВАЛИДАЦИЯ ДЛЯ РЕМЕСЛО (craft)
        elif space_name == 'craft':
            if not video_url and not self.instance.video_url:
                self.add_error('video_url', 'Для пространства РЕМЕСЛО обязательно видео')
            if image:
                self.add_error('image', 'В пространстве РЕМЕСЛО нельзя загружать изображения')
            if not title:
                self.add_error('title', 'Для пространства РЕМЕСЛО обязателен заголовок')
            if not content:
                self.add_error('content', 'Для пространства РЕМЕСЛО обязательно описание')

        # ВАЛИДАЦИЯ ДЛЯ ЧУТКОСТЬ (nerve)
        elif space_name == 'nerve':
            if image:
                self.add_error('image', 'В пространстве ЧУТКОСТЬ нельзя загружать изображения')
            if video_url:
                self.add_error('video_url', 'В пространстве ЧУТКОСТЬ нельзя загружать видео')
            if not title:
                self.add_error('title', 'Для пространства ЧУТКОСТЬ обязателен заголовок')
            if not content:
                self.add_error('content', 'Для пространства ЧУТКОСТЬ обязательно описание')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()

        return instance

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'ОСТАВИТЬ ОТКЛИК...', 'class': 'form-textarea'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].label = ''


class ProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=False, label='ЮЗЕРНЕЙМ')
    display_name = forms.CharField(max_length=100, required=False, label='ВАШЕ ИМЯ')

    class Meta:
        model = Profile
        fields = ['display_name', 'bio', 'avatar', 'banner']
        widgets = {
            'bio': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'ФОТОГРАФ, ДИЗАЙНЕР, ХОДОВИК...\nTG: @username\nIG: @username'}),
            'avatar': forms.FileInput(attrs={'accept': 'image/*'}),
            'banner': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['username'].initial = self.instance.user.username
            self.fields['username'].required = False

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            if self.instance and self.instance.user:
                return self.instance.user.username
            return None

        if self.instance and self.instance.user:
            if User.objects.filter(username=username).exclude(id=self.instance.user.id).exists():
                raise ValidationError('Этот юзернейм уже занят')
        else:
            if User.objects.filter(username=username).exists():
                raise ValidationError('Этот юзернейм уже занят')
        return username

    def save(self, commit=True):
        profile = super().save(commit=False)

        username = self.cleaned_data.get('username')
        if username and self.instance and self.instance.user:
            self.instance.user.username = username
            if commit:
                self.instance.user.save()

        if commit:
            profile.save()
            self.save_m2m()

        return profile


class SearchForm(forms.Form):
    query = forms.CharField(max_length=100, required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'НАЙТИ ВОПРОС...', 'class': 'form-input'}))
    space = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Space
        space_choices = [('all', 'ВСЕ')]
        space_choices += [(s.name, s.get_name_display()) for s in Space.objects.all()]
        self.fields['space'].choices = space_choices