"""Database models for the product catalog."""

from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    """Stamps creation and update times on every model.

    Declared abstract so Django builds no table for it. Each concrete model
    that inherits from it gets its own created_at and updated_at columns.
    """

    created_at = models.DateTimeField(auto_now_add=True)  # set once, on insert
    updated_at = models.DateTimeField(auto_now=True)  # refreshed on every save

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    """A product category that groups many products."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Sets the slug from the name on first save when one is not given."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(TimeStampedModel):
    """A label that can be applied to many products."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Sets the slug from the name on first save when one is not given."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(TimeStampedModel):
    """A catalog item with a unique product number, one category, and many tags."""

    class StockStatus(models.TextChoices):
        IN_STOCK = "IN", "In stock"
        BACKORDER = "BO", "Backorder"
        DISCONTINUED = "DC", "Discontinued"

    product_number = models.CharField(
        max_length=40,
        unique=True,  # unique already builds an index, so no separate db_index
        help_text="Unique product number. Natural key that identifies a product.",
    )
    name = models.CharField(max_length=200, db_index=True)  # searched and ordered on
    description = models.TextField(help_text="Description of the product.")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_status = models.CharField(
        max_length=2,
        choices=StockStatus.choices,
        default=StockStatus.IN_STOCK,
        help_text="Availability from the supplier stock file.",
    )
    # category deletion allowed, but put a product's category_id sets to NULL.
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.product_number} - {self.name}"
