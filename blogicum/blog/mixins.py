from django.http import HttpResponseForbidden
from django.urls import reverse


class CommentSuccessUrlMixin:

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs['post_id']}
        )


class PostSuccessUrlMixin:
    """Миксин для получения URL перенаправления после успешного действия"""

    def get_success_url(self):
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )


class AuthorRequiredMixin:
    """Миксин для проверки авторства"""

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != request.user:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)
