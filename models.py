#!/usr/bin/env python3
"""Database models for the SARYA system."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from app import db

Base = declarative_base()

class ReflexLog(Base):
    """Model for storing reflex system logs."""
    __tablename__ = 'reflex_logs'

    id = Column(Integer, primary_key=True)
    event_type = Column(String(100), nullable=False)
    source = Column(String(100), nullable=False)
    intensity = Column(Float, default=0.0)
    data = Column(JSON, default={})
    response = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow)

class Metric(Base):
    """Model for system metrics tracking."""
    __tablename__ = 'metrics'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    tags = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow)

class Clone(Base):
    """Model for clone management."""
    __tablename__ = 'clones'

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    status = Column(String(50), default='inactive')
    type = Column(String(50), nullable=False)
    config = Column(JSON, default={})
    metrics = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Plugin(Base):
    """Model for plugin management."""
    __tablename__ = 'plugins'

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    enabled = Column(Boolean, default=True)
    config = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class SystemConfig(Base):
    """Model for system configuration."""
    __tablename__ = 'system_config'

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class DiagnosticResult(Base):
    """Diagnostic result model."""
    __tablename__ = 'diagnostic_results'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    module = Column(String(100))
    status = Column(String(50))
    details = Column(JSON, default={})
    severity = Column(String(20))
    category = Column(String(50))
    issue = Column(String(255))
    file = Column(String(255), nullable=True)
    is_resolved = Column(Boolean, default=False)


def init_app(app):
    """Initialize the database with the Flask app."""
    db.init_app(app)
    with app.app_context():
        Base.metadata.create_all(db.engine)