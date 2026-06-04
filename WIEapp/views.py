from datetime import timezone
from django.db.models import Count, Exists, OuterRef, Q, Value
from django.db.models.functions import Coalesce  # если нужно, но для Value достаточно
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse_lazy
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Profile, Impulse, Tag, Comment, Resonance, Landmark, Notification, Space, Report, Warning
from .forms import ImpulseForm, CommentForm, ProfileForm, SearchForm, CustomUserCreationForm
from .utils import generate_verification_token, send_verification_email
from .models import UserQuestion
from django.core.mail import send_mail
from django.conf import settings


def home(request):
    if request.user.is_authenticated:
        return redirect('WIEapp:stream')
    return render(request, 'WIEapp/landing.html')


def error_404(request, exception):
    return render(request, 'WIEapp/errors/404.html', status=404)


def error_403(request, exception):
    return render(request, 'WIEapp/errors/403.html', status=403)


def error_500(request):
    return render(request, 'WIEapp/errors/500.html', status=500)


def csrf_failure(request, reason=""):
    return render(request, 'WIEapp/errors/csrf_failure.html', status=403)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('WIEapp:stream')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        print("=== ФОРМА ОТПРАВЛЕНА ===")
        print("Данные формы:", request.POST)
        print("Ошибки формы:", form.errors)

        if form.is_valid():
            user = form.save()
            print(f"Пользователь создан: {user.username}, id={user.id}")

            # Безопасное создание профиля
            profile, created = Profile.objects.get_or_create(user=user)
            print(f"Профиль создан: {created}, profile_id={profile.id}, user_id={profile.user_id}")

            # Генерация и сохранение токена
            from django.utils.crypto import get_random_string
            token = get_random_string(64)
            profile.email_verification_token = token
            profile.save()
            print(f"Токен сохранён: {profile.email_verification_token}")

            # Отправка письма
            send_verification_email(user, token)
            print("Письмо отправлено")

            return redirect('WIEapp:verify_email_sent')
        else:
            print("ФОРМА НЕ ПРОШЛА ВАЛИДАЦИЮ")
    else:
        form = CustomUserCreationForm()

    return render(request, 'WIEapp/auth/register.html', {'form': form})




def verify_email_sent_view(request):
    return render(request, 'WIEapp/auth/verify_email_sent.html')


def verify_email_view(request, token):
    try:
        profile = Profile.objects.get(email_verification_token=token)

        if profile.is_email_verified:
            return render(request, 'WIEapp/auth/email_already_verified.html')

        profile.is_email_verified = True
        profile.email_verification_token = ''
        profile.save()

        # Редирект НА ЛОГИН, не на register_details
        return redirect('WIEapp:login')

    except Profile.DoesNotExist:
        return render(request, 'WIEapp/auth/email_verify_failed.html')

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(
        recipient=request.user.profile
    ).select_related('sender__user', 'impulse', 'comment').order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    return render(request, 'WIEapp/profile/notifications.html', {
        'notifications': notifications,
        'unread_notifications': unread_count,  # ВАЖНО!
        'has_unread': unread_count > 0,
        'unread_count': unread_count,
    })


@login_required
@require_http_methods(['POST'])
def mark_notification_as_read(request, notification_id):
    """Отметить одно уведомление как прочитанное"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user.profile  # ВАЖНО: .profile
        )
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)


@login_required
@require_http_methods(['POST'])
def delete_notification(request, notification_id):
    """Удалить уведомление"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user.profile  # ВАЖНО: .profile
        )
        notification.delete()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)


@login_required
@require_http_methods(['POST'])
def mark_all_notifications_read(request):
    """Отметить все уведомления пользователя как прочитанные"""
    count = Notification.objects.filter(
        recipient=request.user.profile,
        is_read=False
    ).update(is_read=True)
    return JsonResponse({'status': 'success', 'updated_count': count})

@login_required
def unread_notifications_count(request):
    count = Notification.objects.filter(recipient=request.user.profile, is_read=False).count()
    return JsonResponse({'count': count})


from django.db.models import Exists, OuterRef, Count, Q

@login_required
def stream_view(request):
    mode = request.GET.get('mode', 'all')
    user_profile = request.user.profile

    # Заглушённые пользователи
    muted_users = Landmark.objects.filter(
        follower=user_profile,
        target_type='profile',
        is_muted=True
    ).values_list('target_id', flat=True)

    impulses = Impulse.objects.exclude(author_id__in=muted_users).select_related(
        'author__user', 'space'
    ).prefetch_related('tags').annotate(
        # Подсчёт реакций
        heart_count=Count('resonances', filter=Q(resonances__resonance_type='heart')),
        blast_count=Count('resonances', filter=Q(resonances__resonance_type='blast')),
        # Флаги реакций текущего пользователя
        user_heart=Exists(
            Resonance.objects.filter(
                impulse=OuterRef('pk'),
                user=user_profile,
                resonance_type='heart'
            )
        ),
        user_blast=Exists(
            Resonance.objects.filter(
                impulse=OuterRef('pk'),
                user=user_profile,
                resonance_type='blast'
            )
        )
    )

    if mode == 'followed':
        followed_users = Landmark.objects.filter(
            follower=user_profile,
            target_type='profile'
        ).values_list('target_id', flat=True)
        followed_users = [uid for uid in followed_users if uid != user_profile.id]
        impulses = impulses.filter(author_id__in=followed_users)

    impulses = impulses.order_by('-created_at')

    page = request.GET.get('page', 1)
    paginator = Paginator(impulses, 10)

    try:
        impulses_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        impulses_page = paginator.page(1)

    # AJAX-запрос
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'WIEapp/include/impulse_cards.html', {
            'impulses': impulses_page,
            'has_next': impulses_page.has_next()
        })

    return render(request, 'WIEapp/impulses/stream.html', {
        'impulses': impulses_page,
        'mode': mode,
        'has_next': impulses_page.has_next(),
        'spaces': Space.objects.all(),
        'current_space_name': 'ПОТОК',
    })

@login_required
def spaces_list_view(request):
    spaces = Space.objects.all().order_by('order')
    return render(request, 'WIEapp/spaces_list.html', {'spaces': spaces})


@login_required
@login_required
def space_detail_view(request, space_name):
    space = get_object_or_404(Space, name=space_name)
    mode = request.GET.get('mode', 'all')
    user_profile = request.user.profile

    # Заглушённые пользователи
    muted_users = Landmark.objects.filter(
        follower=user_profile,
        target_type='profile',
        is_muted=True
    ).values_list('target_id', flat=True)

    # Базовый запрос с аннотациями
    impulses = Impulse.objects.filter(space=space).exclude(author_id__in=muted_users).select_related(
        'author__user'
    ).prefetch_related('tags').annotate(
        # Подсчёт реакций
        heart_count=Count('resonances', filter=Q(resonances__resonance_type='heart')),
        blast_count=Count('resonances', filter=Q(resonances__resonance_type='blast')),
        # Флаги реакций текущего пользователя
        user_heart=Exists(
            Resonance.objects.filter(
                impulse=OuterRef('pk'),
                user=user_profile,
                resonance_type='heart'
            )
        ),
        user_blast=Exists(
            Resonance.objects.filter(
                impulse=OuterRef('pk'),
                user=user_profile,
                resonance_type='blast'
            )
        )
    )

    if mode == 'followed':
        followed_users = Landmark.objects.filter(
            follower=user_profile,
            target_type='profile'
        ).values_list('target_id', flat=True)
        followed_users = [uid for uid in followed_users if uid != user_profile.id]
        impulses = impulses.filter(author_id__in=followed_users)

    impulses = impulses.order_by('-created_at')

    page = request.GET.get('page', 1)
    paginator = Paginator(impulses, 10)

    try:
        impulses_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        impulses_page = paginator.page(1)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'WIEapp/include/impulse_cards.html', {
            'impulses': impulses_page,
            'has_next': impulses_page.has_next()
        })

    return render(request, 'WIEapp/impulses/space_detail.html', {
        'impulses': impulses_page,
        'current_space': space,
        'mode': mode,
        'has_next': impulses_page.has_next(),
        'current_space_name': space.get_name_display(),
    })
@login_required
def impulse_detail_view(request, impulse_id):
    impulse = get_object_or_404(
        Impulse.objects.select_related('author__user', 'space'),
        id=impulse_id
    )
    comments = impulse.comments.filter(parent_comment__isnull=True).select_related(
        'author__user'
    ).prefetch_related('replies__author__user')
    user_heart = Resonance.objects.filter(
        user=request.user.profile, impulse=impulse, resonance_type='heart'
    ).exists()
    user_blast = Resonance.objects.filter(
        user=request.user.profile, impulse=impulse, resonance_type='blast'
    ).exists()

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user.profile
            comment.impulse = impulse
            comment.save()
            if impulse.author != request.user.profile:
                Notification.objects.create(
                    recipient=impulse.author,
                    sender=request.user.profile,
                    notification_type='comment',
                    impulse=impulse,
                    comment=comment
                )
            return redirect('WIEapp:impulse_detail', impulse_id=impulse.id)
    else:
        form = CommentForm()

    return render(request, 'WIEapp/impulses/impulse_detail.html', {
        'impulse': impulse,
        'comments': comments,
        'form': form,
        'user': request.user,  # 👈 ЭТО ВАЖНО ДОБАВИТЬ!
        'heart_count': impulse.resonances.filter(resonance_type='heart').count(),
        'blast_count': impulse.resonances.filter(resonance_type='blast').count(),
        'user_heart': user_heart,
        'user_blast': user_blast,

    })


@login_required
def create_impulse_view(request):
    if request.method == 'POST':
        form = ImpulseForm(request.POST, request.FILES)
        if form.is_valid():
            impulse = form.save(commit=False)
            impulse.author = request.user.profile
            impulse.save()
            form.save_m2m()
            return redirect('WIEapp:impulse_detail', impulse_id=impulse.id)
    else:
        form = ImpulseForm()

    return render(request, 'WIEapp/impulses/impulse_form.html', {'form': form, 'editing': False})


@login_required
def edit_impulse_view(request, impulse_id):
    impulse = get_object_or_404(Impulse, id=impulse_id, author=request.user.profile)

    if request.method == 'POST':
        form = ImpulseForm(request.POST, request.FILES, instance=impulse)
        if form.is_valid():
            impulse = form.save(commit=False)
            impulse.is_modified = True
            impulse.save()
            form.save_m2m()
            return redirect('WIEapp:impulse_detail', impulse_id=impulse.id)
    else:
        initial_tags = ', '.join([tag.name for tag in impulse.tags.all()])
        form = ImpulseForm(instance=impulse, initial={'tags': initial_tags})

    return render(request, 'WIEapp/impulses/impulse_form.html', {
        'form': form,
        'editing': True,
        'impulse': impulse
    })


@login_required
def delete_impulse_view(request, impulse_id):
    impulse = get_object_or_404(Impulse, id=impulse_id, author=request.user.profile)

    if request.method == 'POST':
        impulse.delete()
        return redirect('WIEapp:stream')

    return render(request, 'WIEapp/impulses/impulse_confirm_delete.html', {'impulse': impulse})


from django.db.models import Count, Exists, OuterRef, Q


def profile_view(request, username=None):
    if username:
        user = get_object_or_404(User, username=username)
        is_own_profile = False
    else:
        if not request.user.is_authenticated:
            return redirect('WIEapp:login')
        user = request.user
        is_own_profile = True

    profile = get_object_or_404(Profile, user=user)

    # Проверка на заглушку
    if request.user.is_authenticated and not is_own_profile:
        is_muted_by_me = Landmark.objects.filter(
            follower=request.user.profile,
            target_type='profile',
            target_id=profile.id,
            is_muted=True
        ).exists()
        if is_muted_by_me:
            return render(request, 'WIEapp/profile/muted_profile.html', {'profile': profile})

    # Импульсы пользователя С АННОТАЦИЯМИ
    impulses = Impulse.objects.filter(author=profile).select_related('space').annotate(
        heart_count=Count('resonances', filter=Q(resonances__resonance_type='heart')),
        blast_count=Count('resonances', filter=Q(resonances__resonance_type='blast')),
        user_heart=Exists(
            Resonance.objects.filter(
                impulse=OuterRef('pk'),
                user=request.user.profile,
                resonance_type='heart'
            )
        ) if request.user.is_authenticated else Value(False),
        user_blast=Exists(
            Resonance.objects.filter(
                impulse=OuterRef('pk'),
                user=request.user.profile,
                resonance_type='blast'
            )
        ) if request.user.is_authenticated else Value(False)
    ).order_by('-created_at')

    impulses_count = impulses.count()

    # Группировка по пространствам
    impulses_by_space = {}
    for impulse in impulses:
        space_key = impulse.space.name
        if space_key not in impulses_by_space:
            impulses_by_space[space_key] = []
        impulses_by_space[space_key].append(impulse)

    space_order = ['vision', 'nerve', 'craft']
    space_names = {
        'vision': 'ВИДЕНИЕ',
        'nerve': 'ЧУТКОСТЬ',
        'craft': 'РЕМЕСЛО',
    }

    ordered_spaces = []
    for space_key in space_order:
        if space_key in impulses_by_space:
            ordered_spaces.append({
                'name': space_names.get(space_key, space_key.upper()),
                'impulses': impulses_by_space[space_key]
            })

    followers_count = Landmark.objects.filter(target_type='profile', target_id=profile.id).count()
    following_count = Landmark.objects.filter(follower=profile).count()

    is_following = False
    is_muted = False
    if request.user.is_authenticated and request.user.profile != profile:
        landmark = Landmark.objects.filter(
            follower=request.user.profile,
            target_type='profile',
            target_id=profile.id
        ).first()
        if landmark:
            is_following = True
            is_muted = landmark.is_muted

    return render(request, 'WIEapp/profile/profile.html', {
        'profile': profile,
        'impulses_count': impulses_count,
        'ordered_spaces': ordered_spaces,
        'followers_count': followers_count,
        'following_count': following_count,
        'is_own_profile': is_own_profile,
        'is_following': is_following,
        'is_muted': is_muted,
    })


@login_required
def edit_profile_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        # Получаем данные из формы
        display_name = request.POST.get('display_name', '')
        bio = request.POST.get('bio', '')
        new_username = request.POST.get('username', '').strip()

        # Обработка username
        if new_username and new_username != request.user.username:
            # Проверяем, не занят ли username
            if User.objects.filter(username__iexact=new_username).exclude(id=request.user.id).exists():
                messages.error(request, 'Этот username уже занят')
                return redirect('WIEapp:edit_profile')

            # Проверяем валидность username (можно использовать Django валидацию)
            from django.contrib.auth.validators import UnicodeUsernameValidator
            validator = UnicodeUsernameValidator()
            try:
                validator(new_username)
                request.user.username = new_username
                request.user.save()
            except:
                messages.error(request, 'Некорректный username. Используйте буквы, цифры и @/./+/-/_')
                return redirect('WIEapp:edit_profile')

        # Обновляем профиль
        profile.display_name = display_name
        profile.bio = bio

        # Обработка аватара
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']

        # Обработка баннера
        if 'banner' in request.FILES:
            profile.banner = request.FILES['banner']

        profile.save()
        messages.success(request, 'Профиль обновлён!')
        return redirect('WIEapp:user_profile', username=request.user.username)  # замените на ваше имя

    return render(request, 'WIEapp/profile/edit_profile.html', {'profile': profile})


@login_required
def followers_view(request):
    username = request.GET.get('user')
    if username:
        target_user = get_object_or_404(User, username=username)
        target_profile = target_user.profile
    else:
        target_profile = request.user.profile

    print(f"Target profile: {target_profile.user.username}")  # ← отладка

    landmarks = Landmark.objects.filter(
        target_type='profile',
        target_id=target_profile.id
    )
    print(f"Landmarks count: {landmarks.count()}")  # ← отладка

    followers = [lm.follower for lm in landmarks]
    print(f"Followers count: {len(followers)}")  # ← отладка

    return render(request, 'WIEapp/profile/followers.html', {
        'profiles': followers,
        'target_profile': target_profile,
    })


@login_required
def landmarks_view(request):
    username = request.GET.get('user')
    if username:
        target_user = get_object_or_404(User, username=username)
        target_profile = target_user.profile
    else:
        target_profile = request.user.profile

    # Получаем ориентиры target_profile
    landmarks = Landmark.objects.filter(
        follower=target_profile,
        target_type='profile'
    ).select_related('follower__user')

    landmarks_with_target = []
    for lm in landmarks:
        target = Profile.objects.get(id=lm.target_id)
        landmarks_with_target.append({
            'target': target,
            'is_muted': lm.is_muted
        })

    return render(request, 'WIEapp/profile/landmarks.html', {
        'landmarks': landmarks_with_target,
        'target_profile': target_profile,
    })


@login_required
@require_http_methods(['POST'])
def toggle_resonance(request):
    impulse_id = request.POST.get('impulse_id')
    resonance_type = request.POST.get('resonance_type')
    user_profile = request.user.profile

    if resonance_type not in ['heart', 'blast']:
        return JsonResponse({'error': 'invalid type'}, status=400)

    if impulse_id:
        impulse = get_object_or_404(Impulse, id=impulse_id)
        existing = Resonance.objects.filter(
            user=user_profile, impulse=impulse, resonance_type=resonance_type
        ).first()

        if existing:
            existing.delete()
            user_has = False
        else:
            Resonance.objects.create(
                user=user_profile, impulse=impulse, resonance_type=resonance_type
            )
            user_has = True
            if impulse.author != user_profile:
                Notification.objects.create(
                    recipient=impulse.author,
                    sender=user_profile,
                    notification_type='resonance',
                    impulse=impulse,
                    metadata={'resonance_type': resonance_type}
                )

        return JsonResponse({
            'heart_count': impulse.resonances.filter(resonance_type='heart').count(),
            'blast_count': impulse.resonances.filter(resonance_type='blast').count(),
            'user_heart': resonance_type == 'heart' and user_has,
            'user_blast': resonance_type == 'blast' and user_has,
        })

    return JsonResponse({'error': 'no target'}, status=400)

@login_required
@require_http_methods(['POST'])
def add_reply_ajax(request):
    parent_id = request.POST.get('parent_id')
    content = request.POST.get('content')

    if not parent_id or not content:
        return JsonResponse({'status': 'error', 'error': 'Missing data'}, status=400)

    parent_comment = get_object_or_404(Comment, id=parent_id)

    reply = Comment.objects.create(
        author=request.user.profile,
        impulse=parent_comment.impulse,
        content=content,
        parent_comment=parent_comment
    )

    if parent_comment.author != request.user.profile:
        Notification.objects.create(
            recipient=parent_comment.author,
            sender=request.user.profile,
            notification_type='reply',
            impulse=parent_comment.impulse,
            comment=reply
        )

    return JsonResponse({
        'status': 'success',
        'comment_id': reply.id,
        'author_username': reply.author.user.username,
        'author_name': reply.author.display_name or reply.author.user.username,
        'content': reply.content,
        'created_at': reply.created_at.strftime('%d.%m.%Y')
    })

@login_required
@require_http_methods(['POST'])
def toggle_landmark(request):
    target_type = request.POST.get('target_type')
    target_id = request.POST.get('target_id')
    user_profile = request.user.profile

    if target_type not in ['profile', 'space']:
        return JsonResponse({'error': 'invalid type'}, status=400)

    existing = Landmark.objects.filter(
        follower=user_profile, target_type=target_type, target_id=target_id
    ).first()

    if existing:
        existing.delete()
        return JsonResponse({'status': 'removed'})
    else:
        Landmark.objects.create(
            follower=user_profile,
            target_type=target_type,
            target_id=target_id
        )
        if target_type == 'profile':
            target_profile = get_object_or_404(Profile, id=target_id)
            if target_profile != user_profile:
                Notification.objects.create(
                    recipient=target_profile,
                    sender=user_profile,
                    notification_type='landmark'
                )
        return JsonResponse({'status': 'added'})


@login_required
@require_http_methods(['POST'])
def toggle_follow(request):
    target_id = request.POST.get('user_id')
    user_profile = request.user.profile

    if not target_id:
        return JsonResponse({'error': 'no target'}, status=400)

    target_profile = get_object_or_404(Profile, id=target_id)

    existing = Landmark.objects.filter(
        follower=user_profile,
        target_type='profile',
        target_id=target_profile.id
    ).first()

    if existing:
        existing.delete()
        return JsonResponse({'status': 'unfollowed'})
    else:
        Landmark.objects.create(
            follower=user_profile,
            target_type='profile',
            target_id=target_profile.id
        )
        if target_profile != user_profile:
            Notification.objects.create(
                recipient=target_profile,
                sender=user_profile,
                notification_type='landmark'
            )
        return JsonResponse({'status': 'followed'})


@login_required
@require_http_methods(['POST'])
def toggle_mute(request):
    target_id = request.POST.get('user_id')
    user_profile = request.user.profile
    target_profile = get_object_or_404(Profile, id=target_id)

    existing = Landmark.objects.filter(
        follower=user_profile,
        target_type='profile',
        target_id=target_profile.id
    ).first()

    if existing:
        existing.is_muted = not existing.is_muted
        existing.save()
        return JsonResponse({'status': 'muted' if existing.is_muted else 'unmuted'})
    else:
        Landmark.objects.create(
            follower=user_profile,
            target_type='profile',
            target_id=target_profile.id,
            is_muted=True
        )
        return JsonResponse({'status': 'muted'})


@login_required
def report_user(request):
    if request.method == 'POST':
        target_id = request.POST.get('user_id')
        reason = request.POST.get('reason')
        target_profile = get_object_or_404(Profile, id=target_id)

        if target_profile == request.user.profile:
            return JsonResponse({'error': 'Нельзя жаловаться на себя'}, status=400)

        Report.objects.create(
            reporter=request.user.profile,
            reported_user=target_profile,
            reason=reason,
            description=''
        )
        return JsonResponse({'status': 'reported'})
    return JsonResponse({'error': 'invalid method'}, status=400)


def faq_view(request):
    form = SearchForm(request.GET or None)
    return render(request, 'WIEapp/search/faq.html', {'form': form})


@login_required
def ask_question_view(request):
    return render(request, 'WIEapp/search/ask_question.html')


class CustomPasswordResetView(PasswordResetView):
    template_name = 'WIEapp/auth/password_reset.html'
    success_url = reverse_lazy('WIEapp:password_reset_done')
    form_class = PasswordResetForm
    email_template_name = 'WIEapp/auth/password_reset_email.html'


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'WIEapp/auth/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'WIEapp/auth/password_reset_confirm.html'
    success_url = reverse_lazy('WIEapp:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'WIEapp/auth/password_reset_complete.html'


@login_required
@require_http_methods(['POST'])
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    user_profile = request.user.profile

    # Права: автор комментария, автор импульса или админ
    if user_profile == comment.author or user_profile == comment.impulse.author or user_profile.user.is_superuser:
        comment.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'permission denied'}, status=403)



@login_required
@require_http_methods(['POST'])
def warn_user(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'permission denied'}, status=403)

    user_id = request.POST.get('user_id')
    reason = request.POST.get('reason', 'Нарушение правил платформы')

    target_profile = get_object_or_404(Profile, id=user_id)

    if target_profile.user.is_superuser:
        return JsonResponse({'error': 'cannot warn an admin'}, status=400)

    Warning.objects.create(
        user=target_profile,
        moderator=request.user.profile,
        reason=reason
    )

    warnings_count = Warning.objects.filter(user=target_profile, is_active=True).count()
    is_banned = False

    if warnings_count >= 3:
        target_profile.user.is_active = False
        target_profile.user.save()
        is_banned = True

    return JsonResponse({
        'status': 'warned',
        'warnings_count': warnings_count,
        'is_banned': is_banned
    })


@login_required
@require_http_methods(['POST'])
def ban_user(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'permission denied'}, status=403)

    user_id = request.POST.get('user_id')
    reason = request.POST.get('reason', 'Мгновенный бан за грубое нарушение')

    target_profile = get_object_or_404(Profile, id=user_id)

    if target_profile.user.is_superuser:
        return JsonResponse({'error': 'cannot ban an admin'}, status=400)

    target_profile.user.is_active = False
    target_profile.user.save()

    Warning.objects.create(
        user=target_profile,
        moderator=request.user.profile,
        reason=reason
    )

    return JsonResponse({'status': 'banned'})


@login_required
@require_http_methods(['POST'])
def unban_user(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'permission denied'}, status=403)

    user_id = request.POST.get('user_id')
    reason = request.POST.get('reason', 'Разбан по решению администрации')

    target_profile = get_object_or_404(Profile, id=user_id)

    target_profile.user.is_active = True
    target_profile.user.save()

    # Опционально: можно создать уведомление о разбане
    Notification.objects.create(
        recipient=target_profile,
        sender=request.user.profile,
        notification_type='moderation',
        metadata={'action': 'unban', 'reason': reason}
    )

    return JsonResponse({'status': 'unbanned'})


def faq_view(request):
    form = SearchForm(request.GET or None)
    return render(request, 'WIEapp/search/faq.html', {'form': form})

@login_required
def ask_question_api(request):
    if request.method == 'POST':
        topic = request.POST.get('topic')
        question = request.POST.get('question')
        context = request.POST.get('context', '')
        user_profile = request.user.profile
        UserQuestion.objects.create(
            user=user_profile,
            email=user_profile.user.email,
            topic=topic,
            question=question,
            context=context
        )
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def admin_answer_question(request, question_id):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'permission denied'}, status=403)

    question = get_object_or_404(UserQuestion, id=question_id)

    if request.method == 'POST':
        answer = request.POST.get('answer')
        question.answer = answer
        question.status = 'answered'
        question.answered_at = timezone.now()
        question.save()

        # ОТПРАВКА ПИСЬМА ПОЛЬЗОВАТЕЛЮ
        send_mail(
            subject=f'Ответ на ваш вопрос | WHOisE',
            message=f'Здравствуйте!\n\nВы спрашивали:\n"{question.question}"\n\nОтвет администратора:\n{answer}\n\nС уважением, команда WHOisE',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[question.email],
            fail_silently=False,
        )

        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error'}, status=400)


@login_required
def report_impulse(request):
    if request.method == 'POST':
        try:
            impulse_id = request.POST.get('impulse_id')
            reason = request.POST.get('reason')
            description = request.POST.get('description', '')

            impulse = get_object_or_404(Impulse, id=impulse_id)

            Report.objects.create(
                reporter=request.user.profile,
                reported_impulse=impulse,
                reason=reason,
                description=description,
                status='pending'
            )

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'invalid method'}, status=400)

@login_required
def report_user(request):
    if request.method == 'POST':
        target_id = request.POST.get('user_id')
        reason = request.POST.get('reason')
        description = request.POST.get('description', '')

        if not target_id or not reason:
            return JsonResponse({'error': 'Не хватает данных'}, status=400)

        target_profile = get_object_or_404(Profile, id=target_id)

        if target_profile == request.user.profile:
            return JsonResponse({'error': 'Нельзя жаловаться на себя'}, status=400)

        # Проверь, что в модели Report есть поле description
        Report.objects.create(
            reporter=request.user.profile,
            reported_user=target_profile,
            reason=reason,
            description=description,
            status='pending'
        )
        return JsonResponse({'status': 'reported'})

    return JsonResponse({'error': 'invalid method'}, status=400)

@login_required
def report_comment(request):
    if request.method == 'POST':
        comment_id = request.POST.get('comment_id')
        reason = request.POST.get('reason')
        description = request.POST.get('description', '')

        comment = get_object_or_404(Comment, id=comment_id)

        Report.objects.create(
            reporter=request.user.profile,
            reported_comment=comment,
            reason=reason,
            description=description,
            status='pending'
        )

        return JsonResponse({'status': 'success'})

    return JsonResponse({'error': 'invalid method'}, status=400)


@login_required
def edit_comment_view(request, comment_id):
    """Редактирование комментария"""
    comment = get_object_or_404(Comment, id=comment_id)

    # Проверка прав: только автор комментария
    if comment.author != request.user.profile:
        messages.error(request, 'У вас нет прав на редактирование этого комментария')
        return redirect('WIEapp:impulse_detail', impulse_id=comment.impulse.id)

    if request.method == 'POST':
        new_content = request.POST.get('content', '').strip()
        if new_content:
            comment.content = new_content
            comment.is_modified = True
            comment.save()
            messages.success(request, 'Комментарий обновлён')
        return redirect('WIEapp:impulse_detail', impulse_id=comment.impulse.id)

    # GET запрос — показываем форму редактирования
    return render(request, 'WIEapp/include/edit_comment_modal.html', {
        'comment': comment
    })


@login_required
def delete_comment_view(request, comment_id):
    """Удаление комментария с подтверждением"""
    comment = get_object_or_404(Comment, id=comment_id)
    user_profile = request.user.profile

    # Права: автор комментария, автор импульса или админ
    if user_profile != comment.author and user_profile != comment.impulse.author and not user_profile.user.is_superuser:
        messages.error(request, 'У вас нет прав на удаление этого комментария')
        return redirect('WIEapp:impulse_detail', impulse_id=comment.impulse.id)

    if request.method == 'POST':
        impulse_id = comment.impulse.id
        comment.delete()
        messages.success(request, 'Комментарий удалён')
        return redirect('WIEapp:impulse_detail', impulse_id=impulse_id)

    # GET запрос — показываем модальное окно подтверждения
    return render(request, 'WIEapp/include/delete_comment_modal.html', {
        'comment': comment
    })