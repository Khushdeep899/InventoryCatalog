from django.contrib import admin

from .models import Category, Product, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "product_number",
        "name",
        "category",
        "price",
        "stock_status",
        "created_at",
    )
    list_filter = ("category", "tags", "stock_status")
    search_fields = ("product_number", "name", "description")
    filter_horizontal = ("tags",)
    list_select_related = ("category",)  # avoids one extra query per changelist row
    readonly_fields = ("created_at", "updated_at")
