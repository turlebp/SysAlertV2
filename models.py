"""
SQLAlchemy ORM models with encryption support - FIXED
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, Float, ForeignKey, LargeBinary
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Subscription(Base):
    __tablename__ = "subscriptions"
    chat_id = Column(Integer, primary_key=True)
    created_at = Column(Integer)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True, nullable=False, index=True)
    alerts_enabled = Column(Boolean, default=True)
    interval_seconds = Column(Integer, default=60)
    failure_threshold = Column(Integer, default=3)
    created_at = Column(Integer)
    updated_at = Column(Integer)  # ADDED
    
    targets = relationship("Target", cascade="all, delete-orphan", back_populates="customer")


class Target(Base):
    __tablename__ = "targets"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String, nullable=False)
    encrypted_value = Column(LargeBinary, nullable=False)
    fingerprint = Column(String(64), nullable=False, index=True)
    enabled = Column(Boolean, default=True, index=True)
    last_checked = Column(Integer, default=0)
    consecutive_failures = Column(Integer, default=0)
    
    customer = relationship("Customer", back_populates="targets")
class BenchmarkTarget(Base):
    __tablename__ = "benchmark_targets"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, nullable=False, index=True)  # REMOVED unique=True
    encrypted_value = Column(LargeBinary, nullable=False)
    fingerprint = Column(String(64), nullable=False)
    network = Column(String(10), default="mainnet")
    created_at = Column(Integer)
    
class History(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True)
    timestamp = Column(Integer, index=True)
    customer_chat_id = Column(Integer, index=True)
    target_name = Column(String)
    status = Column(String)
    error = Column(Text)
    response_time = Column(Float)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor_chat_id = Column(Integer, index=True)
    action = Column(String)
    details = Column(Text)
    created_at = Column(Integer)