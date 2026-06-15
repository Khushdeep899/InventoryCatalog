"""URL routes for the catalog page and the JSON API."""

from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("api/products/", views.product_api, name="product_api"),
]
