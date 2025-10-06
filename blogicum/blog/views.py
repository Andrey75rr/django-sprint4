from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, UpdateView

from blog.models import Category, Comment, Post
from .forms import CommentForm


POSTS_LIMIT = 5
User = get_user_model()

POSTS_PER_PAGE = 10


def get_published_posts():
    """Получение опубликованных постов с фильтрацией."""
    current_time = timezone.now()
    return Post.objects.filter(
        is_published=True,
        pub_date__lte=current_time,
        category__is_published=True
    ).select_related('author', 'location', 'category').annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')


def get_paginator(request, post_list):
    """Пагинация для списка постов."""
    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def index(request):
    post_list = get_published_posts()
    page_obj = get_paginator(request, post_list)
    context = {'page_obj': page_obj}
    return render(request, 'blog/index.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    post_list = get_published_posts().filter(category=category)
    page_obj = get_paginator(request, post_list)
    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, 'blog/category.html', context)


def post_detail(request, post_id):
    current_time = timezone.now()
    post = get_object_or_404(Post, id=post_id)
    if not post.is_published or (
            post.pub_date > current_time
            or not post.category.is_published):
        if request.user != post.author:
            raise Http404("Пост не найден")
    comments = post.comments.all().order_by('created_at')
    if request.user.is_authenticated:
        form = CommentForm()
    else:
        form = None
    context = {
        'post': post,
        'comments': comments,
        'form': form
    }
    return render(request, 'blog/detail.html', context)


def user_profile(request, username):
    user = get_object_or_404(User, username=username)

    if request.user == user:
        post_list = Post.objects.filter(author=user).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')
    else:
        post_list = get_published_posts().filter(author=user)

    page_obj = get_paginator(request, post_list)
    context = {
        'profile': user,
        'page_obj': page_obj,
        'is_owner': request.user == user
    }
    return render(request, 'blog/profile.html', context)


class UserRegistrationView(CreateView):
    """Регистрация нового пользователя"""

    model = User
    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = '/auth/login/'


class UserUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование профиля пользователя"""

    model = User
    form_class = UserChangeForm
    template_name = 'registration/edit_profile.html'
    success_url = reverse_lazy('blog:index')

    def get_object(self):
        return self.request.user


class PostCreateView(LoginRequiredMixin, CreateView):
    """Создание нового поста"""

    model = Post
    template_name = 'blog/create.html'
    fields = ['title', 'text', 'image', 'pub_date', 'location', 'category']

    def form_valid(self, form):
        """Привязка автора к текущему пользователю"""
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        """Перенаправление в профиль пользователя после создания"""
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )


class PostUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование существующего поста"""

    model = Post
    template_name = 'blog/create.html'
    fields = ['title', 'text', 'image', 'pub_date', 'location', 'category']
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        """Проверка прав на редактирование поста"""
        obj = self.get_object()
        if obj.author != request.user:
            return redirect('blog:post_detail', post_id=obj.id)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """Перенаправление на страницу поста после редактирования"""
        return reverse('blog:post_detail', kwargs={
            'post_id': self.object.id})


class PostDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление поста"""

    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )


class CommentSuccessUrlMixin:

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )


class CommentCreateView(
    LoginRequiredMixin,
    CommentSuccessUrlMixin,
    CreateView
):
    """Создание комментария"""

    model = Comment
    fields = ['text']

    def dispatch(self, request, *args, **kwargs):
        # Проверяем, существует ли пост
        try:
            Post.objects.get(id=self.kwargs['post_id'])
        except Post.DoesNotExist:
            raise Http404("Пост не найден")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post_id = self.kwargs['post_id']
        return super().form_valid(form)


class CommentUpdateView(
    LoginRequiredMixin,
    CommentSuccessUrlMixin,
    UpdateView
):
    """Редактирование комментария"""

    model = Comment
    template_name = 'blog/comment.html'
    fields = ['text']
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)


class CommentDeleteView(
    LoginRequiredMixin,
    CommentSuccessUrlMixin,
    DeleteView
):
    """Удаление комментария"""

    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем пустую форму для совместимости с шаблоном
        context['form'] = forms.Form()
        return context
