"""Management command that ingests a supplier price file (CSV) into the catalog."""

import csv
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from products.models import Category, Product, Tag


class Command(BaseCommand):
    help = "Ingest a supplier price file CSV (idempotent on product number)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the supplier CSV file.")

    def handle(self, *args, **options):
        path = options["csv_path"]
        created = updated = skipped = 0
        errors = []

        try:
            handle = open(path, newline="", encoding="utf-8")
        except OSError as exc:
            raise CommandError(f"Could not open {path}: {exc}")

        valid_status = set(Product.StockStatus.values)

        with handle:
            reader = csv.DictReader(handle)
            for line_no, row in enumerate(reader, start=2):  # row 1 is the header
                try:
                    product_number = row["product_number"].strip()
                    if not product_number:
                        raise ValueError("missing product_number")
                    price = Decimal(row["price"])

                    category = None
                    category_name = row.get("category", "").strip()
                    if category_name:
                        category, _ = Category.objects.get_or_create(name=category_name)

                    stock_status = row.get("stock_status", "").strip().upper()
                    if stock_status not in valid_status:
                        stock_status = Product.StockStatus.IN_STOCK

                    product, was_created = Product.objects.update_or_create(
                        product_number=product_number,
                        defaults={
                            "name": row["name"].strip(),
                            "description": row.get("description", "").strip(),
                            "price": price,
                            "category": category,
                            "stock_status": stock_status,
                        },
                    )

                    tag_names = [
                        t.strip() for t in row.get("tags", "").split("|") if t.strip()
                    ]
                    product.tags.set(
                        Tag.objects.get_or_create(name=name)[0] for name in tag_names
                    )

                    created += was_created
                    updated += not was_created
                except (KeyError, ValueError, InvalidOperation) as exc:
                    skipped += 1
                    errors.append(f"row {line_no}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete. created={created} updated={updated} skipped={skipped}"
            )
        )
        for message in errors:
            self.stdout.write(self.style.WARNING(message))
