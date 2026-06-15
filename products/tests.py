from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import Category, Product, Tag


class ModelTests(TestCase):
    def test_category_renders_as_its_name(self):
        """A Category renders as its name."""
        category = Category.objects.create(name="Lighting")
        self.assertEqual(str(category), "Lighting")

    def test_product_renders_as_product_number_and_name(self):
        """A Product renders as 'product number - name'."""
        product = Product.objects.create(
            product_number="LED-1", name="Bulb", description="warm", price="4.99"
        )
        self.assertEqual(str(product), "LED-1 - Bulb")

    def test_slug_is_generated_from_the_name(self):
        """Saving a Category with no slug derives one from the name."""
        category = Category.objects.create(name="Wire And Cable")
        self.assertEqual(category.slug, "wire-and-cable")

    def test_deleting_a_category_nulls_its_products(self):
        """Deleting a Category keeps its products and clears their category link."""
        category = Category.objects.create(name="Lighting")
        product = Product.objects.create(
            product_number="LED-1",
            name="Bulb",
            description="warm",
            price="4.99",
            category=category,
        )
        category.delete()
        product.refresh_from_db()
        self.assertIsNone(product.category)


class ProductFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lighting = Category.objects.create(name="Lighting")
        cls.wire = Category.objects.create(name="Wire")

        cls.outdoor = Tag.objects.create(name="Outdoor")
        cls.weatherproof = Tag.objects.create(name="Weatherproof")
        cls.led = Tag.objects.create(name="LED")

        # Carries BOTH Outdoor and Weatherproof.
        cls.flood = Product.objects.create(
            product_number="FLOOD",
            name="Flood Light",
            description="bright outdoor floodlight",
            price="24.50",
            category=cls.lighting,
        )
        cls.flood.tags.set([cls.outdoor, cls.weatherproof])

        # Outdoor only.
        cls.cable = Product.objects.create(
            product_number="CABLE",
            name="UF Cable",
            description="buried underground feeder",
            price="168.00",
            category=cls.wire,
        )
        cls.cable.tags.set([cls.outdoor])

        # Weatherproof only.
        cls.box = Product.objects.create(
            product_number="BOX",
            name="WP Box",
            description="gasket enclosure",
            price="7.95",
            category=cls.lighting,
        )
        cls.box.tags.set([cls.weatherproof])

        # Neither of the two test tags.
        cls.bulb = Product.objects.create(
            product_number="BULB",
            name="Indoor Bulb",
            description="warm dimmable lamp",
            price="4.99",
            category=cls.lighting,
        )
        cls.bulb.tags.set([cls.led])

    def get(self, **params):
        return self.client.get(reverse("products:product_list"), params)

    def test_renders_the_product_list_template(self):
        """The list view renders the product_list template."""
        response = self.get()
        self.assertTemplateUsed(response, "products/product_list.html")

    def test_search_matches_the_product_name(self):
        """Searching matches text in the product name."""
        response = self.get(search="Flood")
        self.assertContains(response, "Flood Light")
        self.assertNotContains(response, "UF Cable")

    def test_search_matches_the_description(self):
        """Searching matches text in the description."""
        response = self.get(search="feeder")
        self.assertContains(response, "UF Cable")
        self.assertNotContains(response, "Flood Light")

    def test_search_is_case_insensitive(self):
        """Search ignores case."""
        response = self.get(search="flood")
        self.assertContains(response, "Flood Light")

    def test_category_filter_excludes_other_categories(self):
        """Filtering by category hides products from other categories."""
        response = self.get(category=self.wire.id)
        self.assertContains(response, "UF Cable")
        self.assertNotContains(response, "Flood Light")

    def test_single_tag_filter(self):
        """Filtering by one tag returns only products carrying that tag."""
        response = self.get(tags=self.led.id)
        self.assertContains(response, "Indoor Bulb")
        self.assertNotContains(response, "Flood Light")

    def test_multi_tag_filter_uses_and_semantics(self):
        """Two selected tags return only products that carry BOTH tags."""
        response = self.get(tags=[self.outdoor.id, self.weatherproof.id])
        self.assertContains(response, "Flood Light")  # has both
        self.assertNotContains(response, "UF Cable")  # outdoor only
        self.assertNotContains(response, "WP Box")  # weatherproof only
        self.assertEqual(response.context["result_count"], 1)

    def test_filters_combine(self):
        """Search, category, and tag filters apply together."""
        response = self.get(
            category=self.lighting.id,
            tags=[self.outdoor.id, self.weatherproof.id],
        )
        self.assertContains(response, "Flood Light")
        self.assertNotContains(response, "WP Box")
        self.assertEqual(response.context["result_count"], 1)

    def test_no_matches_shows_empty_state(self):
        """A search with no matches reports zero results."""
        response = self.get(search="nonexistent-term")
        self.assertContains(response, "No products match")
        self.assertEqual(response.context["result_count"], 0)

    def test_non_numeric_filter_params_are_ignored(self):
        """A non-numeric category or tag id is ignored instead of raising a 500."""
        response = self.get(category="abc", tags=["xyz"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result_count"], 4)

    def test_list_view_query_count_does_not_grow_with_products(self):
        """The list view issues a fixed number of queries regardless of catalog size."""
        with CaptureQueriesContext(connection) as first:
            self.get()
        baseline = len(first.captured_queries)

        extra = Category.objects.create(name="Extra")
        for index in range(10):
            product = Product.objects.create(
                product_number=f"X{index}",
                name=f"Extra {index}",
                description="filler",
                price="1.00",
                category=extra,
            )
            product.tags.set([self.led, self.outdoor])

        with CaptureQueriesContext(connection) as second:
            self.get()
        self.assertEqual(len(second.captured_queries), baseline)


class PaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for index in range(15):
            Product.objects.create(
                product_number=f"P{index:02d}",
                name=f"Product {index:02d}",
                description="item",
                price="1.00",
            )

    def test_second_page_holds_the_remaining_products(self):
        """With 15 products and a page size of 12, page 2 holds the other 3."""
        response = self.client.get(reverse("products:product_list"), {"page": 2})
        page_obj = response.context["page_obj"]
        self.assertEqual(page_obj.number, 2)
        self.assertEqual(len(page_obj.object_list), 3)


class JsonApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.outdoor = Tag.objects.create(name="Outdoor")
        cls.weatherproof = Tag.objects.create(name="Weatherproof")

        cls.flood = Product.objects.create(
            product_number="FLOOD",
            name="Flood Light",
            description="bright",
            price="24.50",
        )
        cls.flood.tags.set([cls.outdoor, cls.weatherproof])

        cls.cable = Product.objects.create(
            product_number="CABLE",
            name="UF Cable",
            description="buried",
            price="168.00",
        )
        cls.cable.tags.set([cls.outdoor])

    def test_api_returns_filtered_count_and_shape(self):
        """The JSON API applies the same AND filter and returns the expected shape."""
        response = self.client.get(
            reverse("products:product_api"),
            {"tags": [self.outdoor.id, self.weatherproof.id]},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        result = payload["results"][0]
        self.assertEqual(result["product_number"], "FLOOD")
        self.assertEqual(result["price"], "24.50")
        self.assertEqual(sorted(result["tags"]), ["Outdoor", "Weatherproof"])
