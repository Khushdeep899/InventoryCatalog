"""Integration tests for the import_catalog command and the stock_status field."""

import os
import tempfile
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from products.models import Product

HEADER = "product_number,name,description,price,category,tags,stock_status"


def write_csv(directory, name, rows):
    path = os.path.join(directory, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write(HEADER + "\n")
        for row in rows:
            fh.write(row + "\n")
    return path


class ImportCatalogTests(TestCase):
    def run_import(self, path):
        out = StringIO()
        call_command("import_catalog", path, stdout=out)
        return out.getvalue()

    def test_reimport_updates_in_place_without_duplicates(self):
        """A re-run of import_catalog updates products in place and creates no duplicates."""
        with tempfile.TemporaryDirectory() as directory:
            first = write_csv(
                directory,
                "feed.csv",
                [
                    "X1,Widget,A widget,4.99,Tools,Premium,IN",
                    "X2,Gadget,A gadget,9.99,Tools,Sale,BO",
                ],
            )
            self.run_import(first)
            self.assertEqual(Product.objects.count(), 2)

            second = write_csv(
                directory,
                "feed2.csv",
                [
                    "X1,Widget,A widget,7.50,Tools,Premium,IN",
                    "X2,Gadget,A gadget,9.99,Tools,Sale,BO",
                ],
            )
            self.run_import(second)
            self.assertEqual(Product.objects.count(), 2)  # no duplicates

            widget = Product.objects.get(product_number="X1")
            self.assertEqual(widget.price, Decimal("7.50"))  # updated in place

    def test_import_skips_a_malformed_row(self):
        """A row with an unparseable price is skipped while valid rows still import."""
        with tempfile.TemporaryDirectory() as directory:
            path = write_csv(
                directory,
                "feed.csv",
                [
                    "X1,Widget,A widget,4.99,Tools,Premium,IN",
                    "X2,Bad,Bad price,not-a-number,Tools,Sale,IN",
                ],
            )
            output = self.run_import(path)
            self.assertEqual(Product.objects.count(), 1)
            self.assertIn("skipped=1", output)

    def test_import_sets_category_tags_and_stock_status(self):
        """import_catalog builds the category, tags, and stock status from the row."""
        with tempfile.TemporaryDirectory() as directory:
            path = write_csv(
                directory,
                "feed.csv",
                ["X1,Flood,Outdoor light,24.50,Lighting,LED|Outdoor,BO"],
            )
            self.run_import(path)
            product = Product.objects.get(product_number="X1")
            self.assertEqual(product.category.name, "Lighting")
            self.assertEqual(
                set(product.tags.values_list("name", flat=True)), {"LED", "Outdoor"}
            )
            self.assertEqual(product.stock_status, Product.StockStatus.BACKORDER)


class StockStatusTests(TestCase):
    def test_stock_status_defaults_to_in_stock(self):
        """A product created without a stock status defaults to in stock."""
        product = Product.objects.create(
            product_number="X1", name="Widget", description="x", price="1.00"
        )
        self.assertEqual(product.stock_status, Product.StockStatus.IN_STOCK)

    def test_get_stock_status_display_returns_the_human_label(self):
        """get_stock_status_display returns the human label, not the stored code."""
        product = Product.objects.create(
            product_number="X1",
            name="Widget",
            description="x",
            price="1.00",
            stock_status=Product.StockStatus.BACKORDER,
        )
        self.assertEqual(product.get_stock_status_display(), "Backorder")
