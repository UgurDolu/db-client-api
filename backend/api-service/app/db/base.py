# Import all models for Alembic to detect
from shared.models import Base, QueryStatus, User, UserSettings, Query

# Re-export all models
__all__ = ['Base', 'QueryStatus', 'User', 'UserSettings', 'Query']

# This file is needed for Alembic to discover all models
# All models should be imported here 