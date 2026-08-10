from django.shortcuts import render, redirect, get_object_or_404
from .models import Task
from .forms import TaskForm

# Create your views here.
def task_list(request):
    tasks = Task.objects.filter(project__user=request.user)
    return render(request, 'tasks/task_list.html', {'tasks' : tasks})

def add_task(request):
    form = TaskForm(request.user, request.POST or None)
    if form.is_valid():
        task = form.save(commit=False)
        task.save()
        return redirect('task_list')
    return render(request, 'tasks/task_form.html', {'form' : form})

def update_task(request, id):
    task = get_object_or_404(Task.objects.filter(project__user=request.user), id=id)
    form = TaskForm(request.user, request.POST or None, instance=task)
    if form.is_valid():
        task = form.save(commit=False)
        task.save()
        return redirect('task_list')
    return render(request, 'tasks/task_form.html', {'form' : form})

def delete_task(request, id) :
    task = get_object_or_404(Task.objects.filter(project__user=request.user), id=id)
    if request.method == 'POST' :
        task.delete()
        return redirect('task_list')
    return render(request, 'tasks/confirm_suppr_task.html', {'task' : task})

def task_detail(request, id):
    task = get_object_or_404(Task.objects.filter(project__user=request.user), id=id)
    return render(request, 'tasks/task_detail.html', {'task' : task})