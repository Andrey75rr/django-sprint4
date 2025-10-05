from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.views.generic import CreateView, DeleteView, UpdateView
from django.db.models import Count
from django import forms

from blog.models import Category, Post, Comment


POSTS_LIMIT = 5
User = get_user_model()
POSTS_PER_PAGE = 10


def get_published_posts():
    """Получение опубликованных постов с фильтрацией"""
    current_time = timezone.now()
    return Post.objects.filter(
        is_published=True,
        pub_date__lte=current_time,
        category__is_published=True
    ).select_related('author', 'location', 'category').annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')


def index(request):
    post_list = get_published_posts()
    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, 'blog/index.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    post_list = get_published_posts().filter(category=category)
    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, 'blog/category.html', context)


def post_detail(request, post_id):
    current_time = timezone.now()
    # Сначала получаем пост без фильтров
    post = get_object_or_404(Post, id=post_id)
    # Проверяем права доступа
    if not post.is_published or (
            post.pub_date > current_time
            or not post.category.is_published):
        # Если пост не опубликован, проверяем, является ли пользователь автором
        if request.user != post.author:
            return render(request, 'pages/404.html', status=404)
    comments = post.comments.all().order_by('created_at')
    # Добавляем форму для комментариев
    if request.user.is_authenticated:
        class CommentForm(forms.Form):
            text = forms.CharField(
                widget=forms.Textarea(attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Введите ваш комментарий'
                }),
                label='Комментарий'
            )
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
        # Автор видит все свои посты
        post_list = Post.objects.filter(author=user).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')
    else:
        # Другие видят только опубликованные
        current_time = timezone.now()
        post_list = Post.objects.filter(
            author=user,
            is_published=True,
            pub_date__lte=current_time,
            category__is_published=True
        ).annotate(comment_count=Count('comments')).order_by('-pub_date')

    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
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
        return reverse_lazy(
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
        return reverse_lazy('blog:post_detail', kwargs={
            'post_id': self.object.id})


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    fields = ['text']

    def dispatch(self, request, *args, **kwargs):
        # Проверяем, существует ли пост
        from django.http import Http404
        try:
            # Убираем присвоение переменной, так как она не используется
            Post.objects.get(id=self.kwargs['post_id'])
        except Post.DoesNotExist:
            raise Http404("Пост не найден")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post_id = self.kwargs['post_id']
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    model = Comment
    template_name = 'blog/comment.html'
    fields = ['text']
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем пустую форму для совместимости с шаблоном
        context['form'] = forms.Form()
        return context
