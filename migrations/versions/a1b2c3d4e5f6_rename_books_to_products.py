"""Renombrar books -> products (Névora Moda!)

Revision ID: a1b2c3d4e5f6
Revises: 438168e62fc3
Create Date: 2026-10-21 12:00:00.000000

Convierte el esquema de la tienda de libros al de la tienda de ropa:
  books.title          -> products.name
  books.author         -> products.brand
  books.cover_filename -> products.image_filename
  cart_items.book_id   -> cart_items.product_id
  order_items.book_id  -> order_items.product_id

Solo hace algo si la tabla 'books' todavía existe (bases de datos antiguas).
En una base nueva, creada con db.create_all(), no hace nada.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '438168e62fc3'
branch_labels = None
depends_on = None


def _has_table(name):
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade():
    if not _has_table('books'):
        return

    op.rename_table('books', 'products')
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.alter_column('title', new_column_name='name')
        batch_op.alter_column('author', new_column_name='brand')
        batch_op.alter_column('cover_filename', new_column_name='image_filename')

    for table in ('cart_items', 'order_items'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column('book_id', new_column_name='product_id')


def downgrade():
    if not _has_table('products'):
        return

    for table in ('cart_items', 'order_items'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column('product_id', new_column_name='book_id')

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.alter_column('image_filename', new_column_name='cover_filename')
        batch_op.alter_column('brand', new_column_name='author')
        batch_op.alter_column('name', new_column_name='title')
    op.rename_table('products', 'books')
