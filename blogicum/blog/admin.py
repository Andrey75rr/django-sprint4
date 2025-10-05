from django.contrib import admin

from .models import Category, Location, Post


admin.site.empty_value_display = 'Не задано'
# Задает текст для отображения пустых значений в админке


class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'text',
        'author',
        'is_published',
        'pub_date',
        'category',
        'location'
    )
    list_editable = (
        'is_published',
        'category'
    )
    search_fields = ('title',)
    list_filter = ('category',)
    list_display_links = ('title',)


class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'description',
        'is_published',
        'slug'
    )
    list_editable = ('is_published',)
    search_fields = ('title', 'description')
    list_filter = ('is_published',)
    prepopulated_fields = {'slug': ('title',)}


class LocationAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'is_published'
    )
    list_editable = ('is_published',)
    search_fields = ('name',)
    list_filter = ('is_published',)


# Регистрация моделей с кастомными настройками
admin.site.register(Category, CategoryAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Post, PostAdmin)
