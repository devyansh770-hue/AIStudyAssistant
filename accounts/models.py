from django.contrib.auth.models import AbstractUser
from django.db import models
import random
import string
from django.utils import timezone


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    groups = models.ManyToManyField(
        'auth.Group', verbose_name='groups', blank=True,
        related_name='customuser_set', related_query_name='customuser',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission', verbose_name='user permissions', blank=True,
        related_name='customuser_set', related_query_name='customuser',
    )

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    study_goal_hours = models.PositiveIntegerField(default=2)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - Profile"

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return None


class StudyStreak(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='streak')
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)
    total_active_days = models.IntegerField(default=0)

    def update_streak(self):
        today = timezone.now().date()
        if self.last_active_date is None:
            self.current_streak = 1
            self.total_active_days = 1
        elif self.last_active_date == today:
            return  # Already recorded today
        elif self.last_active_date == today - timezone.timedelta(days=1):
            self.current_streak += 1
            self.total_active_days += 1
        else:
            self.current_streak = 1  # Reset streak
            self.total_active_days += 1
        self.last_active_date = today
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        self.save()

    def __str__(self):
        return f"{self.user.email} — streak: {self.current_streak}"


class OTPVerification(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='otp')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now=True)
    attempts = models.IntegerField(default=0)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)

    def generate(self):
        self.code = ''.join(random.choices(string.digits, k=6))
        self.attempts = 0
        self.save()
        return self.code

    def __str__(self):
        return f"OTP for {self.user.email}"


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now=True)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=15)

    def generate(self):
        self.code = ''.join(random.choices(string.digits, k=6))
        self.attempts = 0
        self.is_used = False
        self.save()
        return self.code

    def __str__(self):
        return f"ResetOTP for {self.user.email}"