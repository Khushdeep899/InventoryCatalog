"""Views for browsing and filtering the product catalog."""

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render

from .models import Category, Product, Tag


def filtered_products(params):
    """Builds the Product queryset shared by the catalog page and the API.

    Applies the search, category, and tag filters from the query string. Tags
    use AND matching, so a product must carry every selected tag.
    """
    # prefetch category and tags to avoid extra queries in the template and API response building.
    qs = Product.objects.select_related("category").prefetch_related("tags")

    # filter 1: search term in name or description
    search = params.get("search", "").strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

    # filter 2: category
    category = params.get("category", "").strip()
    if category.isdigit():  # ids come from the form, ignore anything non-numeric
        qs = qs.filter(category_id=category)

    # filter 3: tags
    tag_ids = [t for t in params.getlist("tags") if t.isdigit()]
    if tag_ids:
        # a product must carry EVERY selected tag, not just one.
        qs = (
            qs.filter(tags__id__in=tag_ids)
            .annotate(
                matched=Count("tags", filter=Q(tags__id__in=tag_ids), distinct=True)
            )
            .filter(matched=len(tag_ids))
        )

    return qs


def product_list(request):
    """Renders the filtered, paginated catalog page."""
    products = filtered_products(request.GET).order_by("name")

    paginator = Paginator(products, 12)  # 12 products per page
    page_obj = paginator.get_page(request.GET.get("page"))

    sticky = request.GET.copy()
    sticky.pop("page", None)  # keep filters in the URL across pages, drop page number

    context = {
        "page_obj": page_obj,
        "result_count": paginator.count,
        "categories": Category.objects.all(),
        "tags": Tag.objects.all(),
        "search": request.GET.get("search", ""),
        "selected_category": request.GET.get("category", ""),
        "selected_tags": request.GET.getlist("tags"),
        "querystring": sticky.urlencode(),
    }
    return render(request, "products/product_list.html", context)


def product_api(request):
    """Returns the filtered products as read-only JSON, matching the catalog page."""
    products = filtered_products(request.GET).order_by(
        "name"
    )  # consistent ordering for pagination and testing
    results = [
        {
            "product_number": product.product_number,
            "name": product.name,
            "description": product.description,
            "price": str(product.price),
            "stock_status": product.get_stock_status_display(),
            "category": product.category.name if product.category else None,
            "tags": [tag.name for tag in product.tags.all()],
        }
        for product in products
    ]
    return JsonResponse({"count": len(results), "results": results})
