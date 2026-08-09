"""
Sample Pydantic schemas for the SQUASH demo backend.

These models represent typical API payloads that benefit from SQUASH compression.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Address(BaseModel):
    """User address model."""
    street: str = Field(description="Street address")
    city: str = Field(description="City name")
    state: str = Field(description="State or province")
    zip_code: str = Field(description="Postal/ZIP code")
    country: str = Field(default="India", description="Country name")


class User(BaseModel):
    """User profile model — demonstrates nested object compaction."""
    id: int = Field(description="User ID")
    name: str = Field(description="Full name")
    email: str = Field(description="Email address")
    age: int = Field(description="Age in years")
    is_active: bool = Field(default=True, description="Account active status")
    address: Address = Field(description="Primary address")
    tags: list[str] = Field(default_factory=list, description="User tags")


class ProductSpec(BaseModel):
    """Product specifications."""
    weight_kg: float = Field(description="Weight in kilograms")
    dimensions: str = Field(description="L x W x H in cm")
    color: str = Field(description="Primary color")


class Product(BaseModel):
    """Product model — demonstrates wide schemas with many fields."""
    id: int
    name: str
    description: str
    price: float
    currency: str = "INR"
    category: str
    in_stock: bool = True
    stock_count: int = 0
    specs: ProductSpec
    tags: list[str] = Field(default_factory=list)


class ComplexProfile(BaseModel):
    """Deeply nested profile demonstrating mixed types, nulls, and arrays."""
    uuid: str
    metadata: dict[str, str | int | None]
    flags: list[bool]
    scores: list[float]
    settings: dict[str, bool]
    notes: str | None = None


# ─── Sample Data ─────────────────────────────────────────────

SAMPLE_USERS: list[User] = [
    User(
        id=1,
        name="Ashwin Kumar",
        email="ashwin@email.com",
        age=28,
        is_active=True,
        address=Address(
            street="123 MG Road",
            city="Mumbai",
            state="Maharashtra",
            zip_code="400001",
            country="India",
        ),
        tags=["developer", "kotlin", "python"],
    ),
    User(
        id=2,
        name="Ravi Sharma",
        email="ravi@email.com",
        age=32,
        is_active=True,
        address=Address(
            street="456 Brigade Road",
            city="Bangalore",
            state="Karnataka",
            zip_code="560001",
            country="India",
        ),
        tags=["designer", "figma"],
    ),
    User(
        id=3,
        name="Priya Patel",
        email="priya@email.com",
        age=26,
        is_active=False,
        address=Address(
            street="789 FC Road",
            city="Pune",
            state="Maharashtra",
            zip_code="411004",
            country="India",
        ),
        tags=["manager", "agile"],
    ),
]

SAMPLE_PRODUCTS: list[Product] = [
    Product(
        id=101,
        name="Kotlin in Action",
        description="Comprehensive guide to Kotlin programming",
        price=2499.00,
        category="Books",
        in_stock=True,
        stock_count=150,
        specs=ProductSpec(weight_kg=0.8, dimensions="24 x 17 x 3", color="Blue"),
        tags=["kotlin", "programming", "jvm"],
    ),
    Product(
        id=102,
        name="Mechanical Keyboard",
        description="Cherry MX Brown switches, RGB backlight",
        price=7999.00,
        category="Electronics",
        in_stock=True,
        stock_count=42,
        specs=ProductSpec(weight_kg=1.2, dimensions="44 x 14 x 4", color="Black"),
        tags=["keyboard", "mechanical", "rgb"],
    ),
]

SAMPLE_COMPLEX = ComplexProfile(
    uuid="123e4567-e89b-12d3-a456-426614174000",
    metadata={"version": 1, "author": "admin", "deleted": None},
    flags=[True, False, True, True],
    scores=[99.9, 85.5, 42.0],
    settings={"dark_mode": True, "notifications": False},
    notes=None,
)
