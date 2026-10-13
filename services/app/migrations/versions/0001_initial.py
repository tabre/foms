"""Initial schema (§3).

Revision ID: 0001
Revises:
Create Date: 2026-10-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String, nullable=False),
        sa.Column("display_name", sa.String, nullable=False, server_default=""),
        sa.Column("credential", sa.String, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("users_username_ci", "users", [text("lower(username)")], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("remember", sa.Boolean, nullable=False, server_default="false"),
    )

    op.create_table(
        "login_throttle",
        sa.Column("username", sa.String, primary_key=True),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "filaments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand", sa.String, nullable=False, server_default=""),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("modifier", sa.String, nullable=False, server_default=""),
        sa.Column("color", sa.String, nullable=False),
        sa.Column("weight_available_g", sa.Numeric(10, 1), nullable=False, server_default="0"),
        sa.Column("low_stock_threshold_g", sa.Numeric(10, 1), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "filaments_unique_ci", "filaments",
        [text("lower(brand)"), text("lower(type)"), text("lower(modifier)"), text("lower(color)")],
        unique=True,
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("default_filament_id", sa.Integer, sa.ForeignKey("filaments.id"), nullable=False),
        sa.Column("weight_per_unit_g", sa.Numeric(10, 1), nullable=False),
        sa.Column("stock_quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("low_stock_threshold", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("products_name_ci", "products", [text("lower(name)")], unique=True)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("customer_first_name", sa.String, nullable=False, server_default=""),
        sa.Column("customer_last_name", sa.String, nullable=False, server_default=""),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False),
        sa.Column("filament_id", sa.Integer, sa.ForeignKey("filaments.id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("filament_required_g", sa.Numeric(12, 1), nullable=False),
        sa.Column("order_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("complete_date", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("item_kind", sa.String, nullable=False),
        sa.Column("item_id", sa.Integer, nullable=False),
        sa.Column("raised_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "alerts_active_unique", "alerts", ["item_kind", "item_id"],
        unique=True, postgresql_where=text("cleared_at IS NULL"),
    )


def downgrade():
    op.drop_table("alerts")
    op.drop_table("orders")
    op.drop_table("products")
    op.drop_table("filaments")
    op.drop_table("login_throttle")
    op.drop_table("sessions")
    op.drop_table("users")
