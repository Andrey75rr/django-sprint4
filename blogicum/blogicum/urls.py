from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from blog.views import UserRegistrationView

handler403 = 'pages.views.csrf_failure'
handler404 = 'pages.views.page_not_found'
handler500 = 'pages.views.server_error'

urlpatterns = [
    path('pages/', include('pages.urls')),
    path('admin/', admin.site.urls),
    path('', include('blog.urls')),  # все URL блога здесь
    path('auth/', include('django.contrib.auth.urls')),
    path(
        'auth/registration/',
        UserRegistrationView.as_view(),
        name='registration'
    ),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += (path('__debug__/', include(debug_toolbar.urls)),)
