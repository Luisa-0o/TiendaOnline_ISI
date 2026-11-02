"""Tallas, tipo de prenda, datos de entrega y método de pago

Cambios (todos aditivos; no se elimina ninguna tabla ni columna):
  * products.garment_type
  * product_sizes (nueva): tallas con existencias propias
  * cart_items.size_id, order_items.size_id / size_label
  * orders: datos de entrega (nullable, los pedidos antiguos quedan sin ellos) y payment_method
  * users.role: se rellenan NULL con 'user' y pasa a NOT NULL

Revision ID: b7e1c2a9d4f3
Revises: a1b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa

revision = "b7e1c2a9d4f3"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
    with op.batch_alter_table("users") as batch:
        batch.alter_column("role", existing_type=sa.String(length=20), nullable=False)

    with op.batch_alter_table("products") as batch:
        batch.add_column(sa.Column("garment_type", sa.String(length=80), nullable=True))

    op.create_table(
        "product_sizes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=20), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_product_sizes_product_id_products", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_product_sizes"),
        sa.UniqueConstraint("product_id", "label", name="uq_product_sizes_product_id_label"),
    )
    op.create_index("ix_product_sizes_product_id", "product_sizes", ["product_id"])

    with op.batch_alter_table("cart_items") as batch:
        batch.add_column(sa.Column("size_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_cart_items_size_id_product_sizes", "product_sizes", ["size_id"], ["id"])

    with op.batch_alter_table("order_items") as batch:
        batch.add_column(sa.Column("size_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("size_label", sa.String(length=20), nullable=True))
        batch.create_foreign_key("fk_order_items_size_id_product_sizes", "product_sizes", ["size_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("recipient_name", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("phone", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("municipality", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("address", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("neighborhood", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("postal_code", sa.String(length=10), nullable=True))
        batch.add_column(sa.Column("address_notes", sa.String(length=300), nullable=True))
        batch.add_column(sa.Column("payment_method", sa.String(length=30), nullable=True))


def downgrade():
    with op.batch_alter_table("orders") as batch:
        for col in ("payment_method", "address_notes", "postal_code", "neighborhood", "address",
                    "municipality", "phone", "recipient_name"):
            batch.drop_column(col)
    with op.batch_alter_table("order_items") as batch:
        batch.drop_constraint("fk_order_items_size_id_product_sizes", type_="foreignkey")
        batch.drop_column("size_label")
        batch.drop_column("size_id")
    with op.batch_alter_table("cart_items") as batch:
        batch.drop_constraint("fk_cart_items_size_id_product_sizes", type_="foreignkey")
        batch.drop_column("size_id")
    op.drop_index("ix_product_sizes_product_id", table_name="product_sizes")
    op.drop_table("product_sizes")
    with op.batch_alter_table("products") as batch:
        batch.drop_column("garment_type")
    with op.batch_alter_table("users") as batch:
        batch.alter_column("role", existing_type=sa.String(length=20), nullable=True)
