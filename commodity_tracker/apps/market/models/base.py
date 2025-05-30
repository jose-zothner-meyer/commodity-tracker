"""
Base abstract models for the market application.
"""
import uuid
from django.db import models
# from django.utils import timezone # Not directly used in these base models

class BaseModel(models.Model):
    """
    Abstract base model that provides common fields for all models.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.__class__.__name__} {self.id}"

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.is_active = False
        self.save()

class TimeStampedModel(models.Model):
    """Abstract base model with auto-managed created_at and updated_at fields."""
    created_at = models.DateTimeField(auto_now_add=True, editable=False, help_text="Timestamp when the record was created.")
    updated_at = models.DateTimeField(auto_now=True, editable=False, help_text="Timestamp when the record was last updated.")

    class Meta:
        abstract = True
        ordering = ['-created_at'] # Default ordering for inheriting models


class UUIDModel(models.Model):
    """Abstract base model using a UUID as the primary key."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, help_text="Unique identifier (UUID).")

    class Meta:
        abstract = True


class ActiveModel(models.Model):
    """Abstract base model providing an 'is_active' flag and methods to manage it."""
    is_active = models.BooleanField(default=True, help_text="Designates whether this record is considered active.")

    class Meta:
        abstract = True

    def activate(self):
        """Activates the instance if it's not already active."""
        if not self.is_active:
            self.is_active = True
            self.save(update_fields=['is_active'])

    def deactivate(self):
        """Deactivates the instance if it's currently active."""
        if self.is_active:
            self.is_active = False
            self.save(update_fields=['is_active']) 