"""Models layer: data access and entity behavior. Own all queries."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src import errors as E


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Filament(Base):
    __tablename__ = "filaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[str] = mapped_column(default="")
    type: Mapped[str] = mapped_column()
    modifier: Mapped[str] = mapped_column(default="")
    color: Mapped[str] = mapped_column()
    weight_available_g: Mapped[Decimal] = mapped_column(Numeric(10, 1), default=Decimal("0"))
    low_stock_threshold_g: Mapped[Decimal] = mapped_column(Numeric(10, 1), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index(
            "filaments_unique_ci",
            text("lower(brand)"), text("lower(type)"),
            text("lower(modifier)"), text("lower(color)"),
            unique=True,
        ),
    )

    # Derived display values
    @property
    def label(self) -> str:
        if self.modifier:
            return f"{self.modifier} {self.color}"
        return self.color

    @property
    def table_name(self) -> str:
        return f"{self.type}, {self.label}"

    @property
    def banner_name(self) -> str:
        return f"{self.label} {self.type}"

    # Entity behavior
    def get_stock(self):
        return self.weight_available_g

    def increase_amount(self, amount: Decimal) -> bool:
        if amount <= 0:
            return False
        self.weight_available_g = Decimal(self.weight_available_g) + Decimal(amount)
        return True

    def decrease_amount(self, amount: Decimal) -> bool:
        amount = Decimal(amount)
        if amount <= 0:
            return False
        if Decimal(self.weight_available_g) < amount:
            return False # Negative result rejected, nothing changes
        self.weight_available_g = Decimal(self.weight_available_g) - amount
        return True

    def is_low_stock(self) -> bool:
        """Strictly less than threshold; threshold 0 never triggers."""
        threshold = Decimal(self.low_stock_threshold_g)
        return threshold > 0 and Decimal(self.weight_available_g) < threshold

    def get_threshold(self):
        return self.low_stock_threshold_g


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    default_filament_id: Mapped[int] = mapped_column(ForeignKey("filaments.id"))
    weight_per_unit_g: Mapped[Decimal] = mapped_column(Numeric(10, 1))
    stock_quantity: Mapped[int] = mapped_column(default=0)
    low_stock_threshold: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    default_filament = relationship("Filament")

    __table_args__ = (Index("products_name_ci", text("lower(name)"), unique=True),)

    def get_stock(self) -> int:
        return self.stock_quantity

    def increase_stock(self, amount: int) -> bool:
        if amount < 1:
            return False
        self.stock_quantity += int(amount)
        return True

    def decrease_stock(self, amount: int) -> bool:
        amount = int(amount)
        if amount < 1:
            return False
        if self.stock_quantity < amount:
            return False
        self.stock_quantity -= amount
        return True

    def is_low_stock(self) -> bool:
        return self.low_stock_threshold > 0 and self.stock_quantity < self.low_stock_threshold

    def get_threshold(self):
        return self.low_stock_threshold


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_first_name: Mapped[str] = mapped_column(default="")
    customer_last_name: Mapped[str] = mapped_column(default="")
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    filament_id: Mapped[int] = mapped_column(ForeignKey("filaments.id"))
    quantity: Mapped[int] = mapped_column()
    filament_required_g: Mapped[Decimal] = mapped_column(Numeric(12, 1))
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    due_date: Mapped[datetime] = mapped_column(Date)
    complete_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product = relationship("Product")
    filament = relationship("Filament")

    def calc_filament_used(self):
        """Snapshot taken at creation."""
        return Decimal(self.filament_required_g)

    def complete_order(self, session) -> str | None:
        """Check the rules, deduct the filament, and mark the order complete in
        the caller's transaction. Returns None on success, or the error constant
        for the rule that failed."""
        if self.complete_date is not None:
            return E.ORDER_ALREADY_COMPLETED
        needed = Decimal(self.filament_required_g)
        filament = session.get(Filament, self.filament_id)
        if Decimal(filament.weight_available_g) < needed:
            return E.INSUFFICIENT_FILAMENT
        filament.weight_available_g = Decimal(filament.weight_available_g) - needed
        self.complete_date = utcnow()
        return None

    def get_status(self) -> str:
        return "Completed" if self.complete_date else "Open"

    def shortage(self) -> bool:
        """True when the available filament is below the amount the order needs."""
        return Decimal(self.filament.weight_available_g) < Decimal(self.filament_required_g)

    @property
    def customer_name(self) -> str:
        return " ".join(p for p in (self.customer_first_name, self.customer_last_name) if p)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column()
    display_name: Mapped[str] = mapped_column(default="")
    credential: Mapped[str] = mapped_column() # Salted adaptive hash
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("users_username_ci", text("lower(username)"), unique=True),)

    def display(self) -> str:
        return self.display_name or self.username

    @property
    def is_active(self) -> bool:
        return bool(self.active)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_kind: Mapped[str] = mapped_column() # 'filament' | 'product'
    item_id: Mapped[int] = mapped_column()
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "alerts_active_unique",
            "item_kind", "item_id",
            unique=True,
            postgresql_where=text("cleared_at IS NULL"),
        ),
    )


class Session(Base):
    """Server-side sessions."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    remember: Mapped[bool] = mapped_column(default=False)

    user = relationship("User")


class LoginThrottle(Base):
    """Failed sign-in tracking per username, shared across workers."""
    __tablename__ = "login_throttle"

    username: Mapped[str] = mapped_column(primary_key=True) # Lowercased
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
