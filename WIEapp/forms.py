from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm, UserCreationForm
from .models import Impulse, Comment, Profile, Tag, Space


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

        # Генерируем уникальный username
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
        fields = ['space', 'title', 'content', 'image', 'video_url', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'ЗАГОЛОВОК ИМПУЛЬСА', 'class': 'form-input'}),
            'content': forms.Textarea(attrs={'rows': 8, 'placeholder': 'ТЕКСТ ИМПУЛЬСА...', 'class': 'form-textarea'}),
            'space': forms.Select(attrs={'class': 'form-select', 'id': 'space-select'}),
            'image': forms.FileInput(attrs={'class': 'form-file', 'accept': 'image/*', 'id': 'media-image'}),
            'video_url': forms.URLInput(
                attrs={'placeholder': 'https://youtu.be/...', 'class': 'form-input', 'id': 'media-video'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['space'].queryset = Space.objects.all()
        if self.instance and self.instance.pk:
            existing_tags = ', '.join([tag.name for tag in self.instance.tags.all()])
            self.fields['tags'].initial = existing_tags

    def clean(self):
        cleaned_data = super().clean()
        space = cleaned_data.get('space')
        image = cleaned_data.get('image')
        video_url = cleaned_data.get('video_url')

        if not space:
            return cleaned_data

        space_name = space.name

        if space_name == 'vision':
            if not image and not self.instance.image:
                self.add_error('image', 'Для пространства ВИДЕНИЕ обязательно изображение')
            if video_url:
                self.add_error('video_url', 'В пространстве ВИДЕНИЕ нельзя загружать видео')
        elif space_name == 'craft':
            if not video_url and not self.instance.video_url:
                self.add_error('video_url', 'Для пространства РЕМЕСЛО обязательно видео')
            if image:
                self.add_error('image', 'В пространстве РЕМЕСЛО нельзя загружать изображения')
        elif space_name == 'nerve':
            if image:
                self.add_error('image', 'В пространстве ЧУТКОСТЬ нельзя загружать изображения')
            if video_url:
                self.add_error('video_url', 'В пространстве ЧУТКОСТЬ нельзя загружать видео')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            tag_string = self.cleaned_data.get('tags', '')
            if tag_string:
                instance.tags.clear()
                tags = [t.strip().lower() for t in tag_string.split(',') if t.strip()]
                for tag_name in tags:
                    if tag_name.startswith('#'):
                        tag_name = tag_name[1:]
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    instance.tags.add(tag)
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
    username = forms.CharField(max_length=150, required=True, label='ЮЗЕРНЕЙМ')
    display_name = forms.CharField(max_length=100, required=True, label='ВАШЕ ИМЯ')

    class Meta:
        model = Profile
        fields = ['display_name', 'bio']
        widgets = {
            'bio': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'ФОТОГРАФ, ДИЗАЙНЕР, ХОДОВИК...\nTG: @username\nIG: @username'})
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Этот юзернейм уже занят')
        return username


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