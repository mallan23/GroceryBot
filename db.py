# defines the SQLalchemy engine and the ORM database models for the meal planning application

import os
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    func,
    create_engine,
    PrimaryKeyConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TEXT, CITEXT, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

# Meal Plan ORM model
class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    dietary_tags = Column(
        ARRAY(TEXT),
        server_default="{}",
        nullable=False,
    )
    plan_json = Column(
        JSONB,
        nullable=False,
    )

    shopping_items = relationship(
        "ShoppingItem",
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

# Meal ORM model
class Meal(Base):
    __tablename__ = "meals"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    meal_name = Column(CITEXT, unique=True, nullable=False)
    description = Column(CITEXT, nullable=True)

    ingredients = relationship(
        "MealIngredient",
        back_populates="meal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

# Meal Ingredient ORM model
class MealIngredient(Base):
    __tablename__ = "meal_ingredients"
    __table_args__ = (
        PrimaryKeyConstraint("meal_id", "name", name="pk_meal_ingredient"),
    )

    meal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meals.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(CITEXT, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(CITEXT, nullable=False)

    meal = relationship("Meal", back_populates="ingredients")

# Shopping Item ORM model
class ShoppingItem(Base):
    __tablename__ = "shopping_items"
    __table_args__ = (
        PrimaryKeyConstraint("plan_id", "name", name="pk_shopping_item"),
    )

    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meal_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(CITEXT, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(CITEXT, nullable=False)

    plan = relationship("MealPlan", back_populates="shopping_items")


# Database connection setup
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Fuckmakingpasswords69@34.1.186.26:5432/GroceryBot_db1",
)

# Create the database engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    client_encoding="utf8",
    future=True,
)

# Create a configured "Session" class
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)

# base.metadata contains the definitions for all tables, will create them if thet dont exist, if they do exist it will do nothing (no alter)
Base.metadata.create_all(bind=engine)