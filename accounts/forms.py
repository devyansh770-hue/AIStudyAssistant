

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
import re
from .models import CustomUser, UserProfile


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password',
            'id': 'password1'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm Password'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input', 'placeholder': 'Email address'
            }),
        }

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        errors = []
        if len(password) < 8:
            errors.append('At least 8 characters.')
        if not re.search(r'[A-Z]', password):
            errors.append('At least one uppercase letter.')
        if not re.search(r'[a-z]', password):
            errors.append('At least one lowercase letter.')
        if not re.search(r'\d', password):
            errors.append('At least one number.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-]', password):
            errors.append('At least one special character (!@#$%^&* etc).')
        if errors:
            raise ValidationError(errors)
        return password

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError('Passwords do not match.')
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_verified = False
        user.is_active = False   # inactive until OTP verified
        if commit:
            user.save()
        return user


class OTPForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-input otp-input',
            'placeholder': '______',
            'maxlength': '6',
            'autocomplete': 'off',
            'style': 'letter-spacing: 12px; font-size: 1.5rem; text-align:center'
        })
    )

    def clean_code(self):
        code = self.cleaned_data.get('code', '')
        if not code.isdigit():
            raise ValidationError('OTP must be 6 digits only.')
        return code


class LoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-input', 'placeholder': 'Email address'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-input', 'placeholder': 'Password',
        'id': 'loginPassword'
    }))


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-input', 'placeholder': 'Your registered email'
    }))


class PasswordResetConfirmForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'New Password',
            'id': 'newPassword'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input', 'placeholder': 'Confirm New Password'
        })
    )

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        errors = []
        if len(password) < 8:
            errors.append('At least 8 characters.')
        if not re.search(r'[A-Z]', password):
            errors.append('At least one uppercase letter.')
        if not re.search(r'\d', password):
            errors.append('At least one number.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-]', password):
            errors.append('At least one special character.')
        if errors:
            raise ValidationError(errors)
        return password

    def clean_confirm_password(self):
        p1 = self.cleaned_data.get('new_password')
        p2 = self.cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise ValidationError('Passwords do not match.')
        return p2


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'study_goal_hours', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3
            }),
            'study_goal_hours': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'max': 16
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control', 'accept': 'image/*', 'id': 'avatarInput'
            }),
        }