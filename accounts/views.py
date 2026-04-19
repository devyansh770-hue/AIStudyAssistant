import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django_ratelimit.decorators import ratelimit
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import CustomUser, UserProfile, OTPVerification, PasswordResetOTP, StudyStreak
from .forms import (RegisterForm, OTPForm, LoginForm,
                    PasswordResetRequestForm, PasswordResetConfirmForm, ProfileForm)
from .utils import send_otp_email

logger = logging.getLogger(__name__)


def _update_streak(user):
    streak, _ = StudyStreak.objects.get_or_create(user=user)
    streak.update_streak()


def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    return render(request, 'landing.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            StudyStreak.objects.create(user=user)
            otp_obj, _ = OTPVerification.objects.get_or_create(user=user)
            code = otp_obj.generate()
            try:
                send_otp_email(user.email, code, 'verification')
                request.session['otp_user_id'] = user.id
                messages.success(request, f'OTP sent to {user.email}')
                return redirect('accounts:verify_otp')
            except Exception as e:
                logger.error(f"OTP email failed: {e}", exc_info=True)
                user.delete()
                messages.error(request, 'Failed to send OTP. Check email settings.')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def verify_otp(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('accounts:register')
    try:
        user = CustomUser.objects.get(pk=user_id)
        otp_obj = OTPVerification.objects.get(user=user)
    except (CustomUser.DoesNotExist, OTPVerification.DoesNotExist):
        return redirect('accounts:register')

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            entered = form.cleaned_data['code']
            if otp_obj.attempts >= 5:
                messages.error(request, 'Too many wrong attempts. Please register again.')
                user.delete()
                return redirect('accounts:register')
            if otp_obj.is_expired():
                messages.error(request, 'OTP expired. Please register again.')
                user.delete()
                return redirect('accounts:register')
            if entered == otp_obj.code:
                user.is_active = True
                user.is_verified = True
                user.save()
                otp_obj.delete()
                del request.session['otp_user_id']
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                _update_streak(user)
                messages.success(request, f'Welcome {user.username}! Email verified.')
                return redirect('dashboard:home')
            else:
                otp_obj.attempts += 1
                otp_obj.save()
                remaining = 5 - otp_obj.attempts
                messages.error(request, f'Wrong OTP. {remaining} attempts left.')
    else:
        form = OTPForm()
    return render(request, 'accounts/verify_otp.html', {
        'form': form, 'email': user.email, 'attempts_left': 5 - otp_obj.attempts,
    })


def resend_otp(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('accounts:register')
    try:
        user = CustomUser.objects.get(pk=user_id)
        otp_obj, _ = OTPVerification.objects.get_or_create(user=user)
        code = otp_obj.generate()
        send_otp_email(user.email, code, 'verification')
        messages.success(request, 'New OTP sent!')
    except Exception:
        messages.error(request, 'Failed to resend. Try again.')
    return redirect('accounts:verify_otp')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user:
                if not user.is_verified:
                    messages.error(request, 'Please verify your email first.')
                    return redirect('accounts:login')
                login(request, user)
                _update_streak(user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('dashboard:home')
        messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Logged out successfully.')
    return redirect('accounts:login')


@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email, is_verified=True)
                otp_obj, _ = PasswordResetOTP.objects.get_or_create(user=user)
                code = otp_obj.generate()
                send_otp_email(email, code, 'reset')
                request.session['reset_user_id'] = user.id
                messages.success(request, f'OTP sent to {email}')
                return redirect('accounts:password_reset_verify')
            except CustomUser.DoesNotExist:
                messages.success(request, 'If that email is registered, an OTP has been sent.')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'accounts/password_reset_request.html', {'form': form})


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def password_reset_verify(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('accounts:password_reset_request')
    try:
        user = CustomUser.objects.get(pk=user_id)
        otp_obj = PasswordResetOTP.objects.filter(user=user, is_used=False).latest('created_at')
    except Exception:
        return redirect('accounts:password_reset_request')
    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            entered = form.cleaned_data['code']
            if otp_obj.attempts >= 5:
                messages.error(request, 'Too many attempts. Request a new OTP.')
                return redirect('accounts:password_reset_request')
            if otp_obj.is_expired():
                messages.error(request, 'OTP expired. Request a new one.')
                return redirect('accounts:password_reset_request')
            if entered == otp_obj.code:
                request.session['reset_verified'] = True
                otp_obj.is_used = True
                otp_obj.save()
                return redirect('accounts:password_reset_confirm')
            else:
                otp_obj.attempts += 1
                otp_obj.save()
                messages.error(request, f'Wrong OTP. {5 - otp_obj.attempts} attempts left.')
    else:
        form = OTPForm()
    return render(request, 'accounts/password_reset_verify.html', {'form': form, 'email': user.email})


def password_reset_confirm(request):
    user_id = request.session.get('reset_user_id')
    verified = request.session.get('reset_verified')
    if not user_id or not verified:
        return redirect('accounts:password_reset_request')
    try:
        user = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist:
        return redirect('accounts:password_reset_request')
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            del request.session['reset_user_id']
            del request.session['reset_verified']
            messages.success(request, 'Password reset! Please login.')
            return redirect('accounts:login')
    else:
        form = PasswordResetConfirmForm()
    return render(request, 'accounts/password_reset_confirm.html', {'form': form})


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    streak, _ = StudyStreak.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            new_username = request.POST.get('username', '').strip()
            if new_username:
                request.user.username = new_username
                request.user.save()
            messages.success(request, 'Profile updated!')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'accounts/profile.html', {
        'form': form, 'profile': profile, 'streak': streak
    })

from django.contrib.auth import get_user_model
from django.http import HttpResponse

User = get_user_model()

def reset_admin_password(request):
    users = User.objects.all().values('email', 'is_verified', 'is_superuser')
    return HttpResponse(list(users))