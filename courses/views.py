from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Course, Topic
from .forms import CourseForm

@login_required
def course_list(request):
    courses = Course.objects.filter(user=request.user)
    return render(request, 'courses/course_list.html', {'courses': courses})


@login_required
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.user = request.user
            course.save()
            messages.success(request, f'Course "{course.name}" created!')
            return redirect('courses:detail', pk=course.pk)
    else:
        form = CourseForm()
    return render(request, 'courses/course_create.html', {'form': form})


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    topics = course.topic_set.all()
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'topics': topics,
    })


@login_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated!')
            return redirect('courses:detail', pk=course.pk)
    else:
        form = CourseForm(instance=course)
    return render(request, 'courses/course_create.html', {
        'form': form, 'edit': True, 'course': course
    })


@login_required
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == 'POST':
        course.delete()
        messages.success(request, 'Course deleted.')
        return redirect('courses:list')
    return render(request, 'courses/course_confirm_delete.html', {'course': course})


@login_required
def log_hours(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == 'POST':
        hours = float(request.POST.get('hours', 0))
        course.hours_spent += hours
        course.save()
        messages.success(request, f'{hours} hours logged!')
    return redirect('courses:detail', pk=pk)


@login_required
def topic_toggle(request, pk):
    topic = get_object_or_404(Topic, pk=pk, course__user=request.user)
    topic.is_completed = not topic.is_completed
    topic.save()
    return redirect('courses:detail', pk=topic.course.pk)