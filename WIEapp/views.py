from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import Profile, Impulse, Tag, Comment, Resonance, Landmark, Notification, Space
from .forms import ImpulseForm, CommentForm, ProfileForm, SearchForm, CustomUserCreationForm
from .utils import generate_verification_token, send_verification_email

def home(request):
    if request.user.is_authenticated:
        return redirect('WIEapp:stream')
    return render(request, 'WIEapp/landing.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('WIEapp:stream')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Генерируем токен и сохраняем в профиль
            profile = user.profile
            profile.email_verification_token = generate_verification_token()
            profile.save()

            # Отправляем письмо
            send_verification_email(user)

            # Редиректим на страницу "проверьте почту"
            return redirect('WIEapp:verify_email_sent')
    else:
        form = CustomUserCreationForm()

    return render(request, 'WIEapp/auth/register.html', {'form': form})

def register_details_view(request):
    user_id = request.session.get('new_user_id')
    if not user_id:
        return redirect('WIEapp:register')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('WIEapp:register')

    # Проверяем, подтверждён ли email
    if not user.profile.is_email_verified:
        # Если нет — отправляем на повторную отправку письма или на регистрацию
        return redirect('WIEapp:verify_email_sent')

    if request.user.is_authenticated and request.user.id != user_id:
        return redirect('WIEapp:stream')

    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            new_username = form.cleaned_data.get('username')
            if new_username and not User.objects.filter(username=new_username).exists():
                user.username = new_username
                user.save()

            profile = user.profile
            profile.display_name = form.cleaned_data.get('display_name')
            profile.bio = form.cleaned_data.get('bio', '')
            profile.save()

            if 'new_user_id' in request.session:
                del request.session['new_user_id']

            return redirect('WIEapp:login')
    else:
        form = ProfileForm()

    return render(request, 'WIEapp/auth/register_details.html', {'form': form})

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

        # Сохраняем user_id в сессию для заполнения профиля
        request.session['new_user_id'] = profile.user.id

        return redirect('WIEapp:register_details')

    except Profile.DoesNotExist:
        return render(request, 'WIEapp/auth/email_verify_failed.html')


@login_required
def unread_notifications_count(request):
    count = Notification.objects.filter(recipient=request.user.profile, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def stream_view(request):
    impulses = Impulse.objects.all().select_related(
        'author__user', 'space'
    ).prefetch_related('tags', 'resonances').order_by('-created_at')

    page = request.GET.get('page', 1)
    paginator = Paginator(impulses, 10)

    try:
        impulses_page = paginator.page(page)
    except PageNotAnInteger:
        impulses_page = paginator.page(1)
    except EmptyPage:
        impulses_page = paginator.page(paginator.num_pages)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'WIEapp/partials/impulse_cards.html', {'impulses': impulses_page})

    return render(request, 'WIEapp/impulses/stream.html', {
        'impulses': impulses_page,
        'spaces': Space.objects.all()
    })


@login_required
def space_view(request, space_name):
    space = get_object_or_404(Space, name=space_name)
    impulses = Impulse.objects.filter(space=space).select_related(
        'author__user'
    ).prefetch_related('tags', 'resonances').order_by('-created_at')

    page = request.GET.get('page', 1)
    paginator = Paginator(impulses, 10)
    impulses_page = paginator.get_page(page)

    return render(request, 'WIEapp/impulses/space.html', {
        'impulses': impulses_page,
        'current_space': space,
        'spaces': Space.objects.all()
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
    impulses = Impulse.objects.filter(author=profile).order_by('-created_at')
    followers_count = Landmark.objects.filter(target_type='profile', target_id=profile.id).count()
    following_count = Landmark.objects.filter(follower=profile).count()

    return render(request, 'WIEapp/profile/profile.html', {
        'profile': profile,
        'impulses': impulses,
        'followers_count': followers_count,
        'following_count': following_count,
        'is_own_profile': is_own_profile
    })


@login_required
def edit_profile_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('WIEapp:profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'WIEapp/profile/edit_profile.html', {'form': form})


@login_required
def landmarks_view(request):
    landmarks = Landmark.objects.filter(follower=request.user.profile).select_related('follower__user')
    return render(request, 'WIEapp/profile/landmarks.html', {'landmarks': landmarks})


@login_required
def followers_view(request):
    followers = Landmark.objects.filter(
        target_type='profile', target_id=request.user.profile.id
    ).select_related('follower__user')
    return render(request, 'WIEapp/profile/followers.html', {'followers': followers})


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(
        recipient=request.user.profile
    ).select_related('sender__user', 'impulse', 'comment').order_by('-created_at')

    unread = notifications.filter(is_read=False)
    unread.update(is_read=True)

    return render(request, 'WIEapp/profile/notifications.html', {'notifications': notifications})


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
        else:
            Resonance.objects.create(
                user=user_profile, impulse=impulse, resonance_type=resonance_type
            )
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
        })

    return JsonResponse({'error': 'no target'}, status=400)


@login_required
@require_http_methods(['POST'])
def add_reply_ajax(request):
    parent_id = request.POST.get('parent_id')
    content = request.POST.get('content')
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
        'author': reply.author.user.username,
        'content': reply.content,
        'created_at': reply.created_at.strftime('%d.%m.%Y %H:%M')
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


def faq_view(request):
    form = SearchForm(request.GET or None)
    return render(request, 'WIEapp/search/faq.html', {'form': form})


@login_required
def ask_question_view(request):
    return render(request, 'WIEapp/search/ask_question.html')


def password_reset_view(request):
    return render(request, 'WIEapp/auth/password_reset.html')


def password_reset_done_view(request):
    return render(request, 'WIEapp/auth/password_reset_done.html')


def password_reset_confirm_view(request, uidb64, token):
    return render(request, 'WIEapp/auth/password_reset_confirm.html', {
        'uidb64': uidb64,
        'token': token
    })


def password_reset_complete_view(request):
    return render(request, 'WIEapp/auth/password_reset_complete.html')