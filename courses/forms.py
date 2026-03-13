from django import forms
from .models import Course, Topic

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'description', 'exam_date', 'complexity', 'topics', 'daily_study_hours']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Data Structures & Algorithms'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Short description...'}),
            'exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'complexity': forms.Select(attrs={'class': 'form-select'}),
            'topics': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Arrays, Linked Lists, Trees, Sorting, Graphs'}),
            'daily_study_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
        }


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ['name', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Topic name'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }