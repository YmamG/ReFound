from django.utils.translation import gettext_lazy as _
import uuid
import secrets

from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator, validate_email
from django.db import models
from django.conf import settings
from datetime import timedelta
from django.utils import timezone


def not_future(value):
    if value > timezone.localdate():
        raise ValidationError(_("The date cannot be in the future."))


def device_number():
    return str(secrets.randbelow(90_000_000) + 10_000_000)


class Device(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(max_length=8, unique=True, default=device_number, editable=False)
    credential_hash = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.number


class Report(models.Model):
    class Building(models.TextChoices):
        STUDENTS = "students", _("Men’s building")
        WOMEN = "women", _("Women’s building")

    class Kind(models.TextChoices):
        LOST = "lost", _("Lost")
        FOUND = "found", _("Found")

    class Category(models.TextChoices):
        ELECTRONICS = "electronics", _("Electronics")
        DOCUMENTS = "documents", _("Documents")
        KEYS = "keys", _("Keys")
        CLOTHING = "clothing", _("Clothing")
        BAGS = "bags", _("Bags")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        MATCHED = "matched", _("Potentially matched")
        RESOLVED = "resolved", _("Resolved")

    class Contact(models.TextChoices):
        EMAIL = "email", _("Email")
        PHONE = "phone", _("Phone")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL, related_name="reports")
    building = models.CharField(max_length=12, choices=Building.choices, blank=True, db_index=True)
    classroom = models.CharField(max_length=30, blank=True, help_text=_("Optional classroom or lab number, e.g. A-204. Never share access codes."))
    kind = models.CharField(max_length=5, choices=Kind.choices)
    title = models.CharField(max_length=120, validators=[MinLengthValidator(3)])
    description = models.TextField(max_length=3000, validators=[MinLengthValidator(10)])
    category = models.CharField(max_length=20, choices=Category.choices)
    color = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=120, help_text=_("General area only, e.g. campus library. No room numbers or addresses."))
    event_date = models.DateField(validators=[not_future])
    image = models.ImageField(upload_to="reports/%Y/%m/", blank=True)
    contact_method = models.CharField(max_length=5, choices=Contact.choices)
    contact_info = models.CharField(max_length=254)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    is_hidden = models.BooleanField(default=False, db_index=True)
    management_hash = models.CharField(max_length=128, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["kind", "status", "category", "-created_at"]), models.Index(fields=["event_date"])]

    def clean(self):
        super().clean()
        try:
            if self.contact_method == self.Contact.EMAIL:
                validate_email(self.contact_info)
            elif self.contact_method == self.Contact.PHONE:
                RegexValidator(r"^\+?[0-9 ()-]{7,25}$", _("Enter a valid phone number."))(self.contact_info)
        except ValidationError as exc:
            raise ValidationError({"contact_info": exc.messages})

    @property
    def is_archived(self):
        return self.created_at <= timezone.now() - timedelta(days=settings.REFOUND_ARCHIVE_DAYS)

    def __str__(self):
        return self.title


class Claim(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="claims")
    message = models.TextField(max_length=2000)
    reply_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class AbuseReport(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="abuse_reports")
    reason = models.TextField(max_length=1000)
    reviewed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SubmissionWindow(models.Model):
    # HMAC of the client IP; no raw network address is retained.
    key = models.CharField(max_length=64, primary_key=True)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    count = models.PositiveIntegerField(default=0)
