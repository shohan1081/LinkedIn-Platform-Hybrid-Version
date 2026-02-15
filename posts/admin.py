from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import Tag, Image, NeedPost, OfferPost

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class ImageInline(GenericTabularInline):
    model = Image
    extra = 1
    ct_field = 'post_content_type'
    ct_fk_field = 'post_object_id'

@admin.register(NeedPost)
class NeedPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'description')
    inlines = [ImageInline] # Using the GenericTabularInline here

    def author(self, obj):
        return obj.author
    author.short_description = 'Author'

@admin.register(OfferPost)
class OfferPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'price_range', 'delivery_time', 'created_at', 'updated_at')
    list_filter = ('category', 'delivery_time', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'price_range')
    inlines = [ImageInline] # Using the GenericTabularInline here

    def author(self, obj):
        return obj.author
    author.short_description = 'Author'