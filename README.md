# InventoryCatalog

A small Django catalog of products, categories, and tags with a search and filter
page. Search matches a product name or description, results can be filtered by
category and by one or more tags (a product must carry every selected tag), and all
of these combine. A read-only JSON endpoint exposes the same filtered data.

## Tech stack

- Python 3.12, Django 5.2
- SQLite (zero setup)
- Django templates for the front end

## Quickstart

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata sample_data       # load the sample catalog
python manage.py runserver
```

Open http://127.0.0.1:8000/ for the catalog and
http://127.0.0.1:8000/api/products/ for the JSON feed.

To browse or edit data in the admin:

```bash
python manage.py createsuperuser
# then visit http://127.0.0.1:8000/admin/
```

## Running the tests

```bash
python manage.py test
```

## Data model

- **Category**: a grouping for products. A product belongs to at most one category.
- **Tag**: a label that can be applied to many products.
- **Product**: a catalog item with a unique `product_number` (its natural key), a
  name, a description, a price, one optional category, and many tags.

Deleting a category sets its products' category to null (`on_delete=SET_NULL`)
rather than deleting the products, so catalog entries are never lost when a
category is removed.

## How filtering works

- Search is a case-insensitive match against the product name and description.
- Category filtering is an exact match on the selected category.
- Tag filtering uses AND semantics: a product is shown only if it carries every
  selected tag. This is implemented as one annotated query (a count of matched tags
  filtered down to those equal to the number requested), not a per-tag loop.
- The queryset uses `select_related` for the category and `prefetch_related` for
  the tags, so the page and API render with a fixed number of queries regardless of
  how many products are shown.

The HTML view and the JSON API share a single `filtered_products` helper, so both
apply identical filtering.

## Configuration

Settings read from environment variables with development fallbacks, so no real
secret is committed. See `.env.example`. For production set `DJANGO_SECRET_KEY`,
`DJANGO_DEBUG=False`, and `DJANGO_ALLOWED_HOSTS`.

## Assumptions and notes

- Sample data was created through the Django admin and exported as a fixture
  (`products/fixtures/sample_data.json`) so the project ships with reproducible
  data that loads in one command.
- Slugs for categories and tags are generated from the name on save. Two names that
  slugify to the same value would collide on the unique constraint; a production
  version would append a numeric suffix.
- Styling is intentionally minimal, since the brief states design is not graded.

## AI usage

I used AI tools as a coding assistant and reference while building this project.
All code was written, reviewed, and is fully understood by me, and I can explain
any part of the implementation.
