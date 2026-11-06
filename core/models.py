import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator, validate_email
from django.db import models
from django.utils import timezone


def not_future(value):
    if value > timezone.localdate():
        raise ValidationError("The date cannot be in the future.")


class Report(models.Model):
    class Kind(models.TextChoices):
        LOST = "lost", "Lost"
        FOUND = "found", "Found"

    class Category(models.TextChoices):
        ELECTRONICS = "electronics", "Electronics"
        DOCUMENTS = "documents", "Documents"
        KEYS = "keys", "Keys"
        CLOTHING = "clothing", "Clothing"
        BAGS = "bags", "Bags"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        MATCHED = "matched", "Potentially matched"
        RESOLVED = "resolved", "Resolved"

    class Contact(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=5, choices=Kind.choices)
    title = models.CharField(max_length=120, validators=[MinLengthValidator(3)])
    description = models.TextField(max_length=3000, validators=[MinLengthValidator(10)])
    category = models.CharField(max_length=20, choices=Category.choices)
    color = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=120, help_text="General area only, e.g. campus library. No room numbers or addresses.")
    event_date = models.DateField(validators=[not_future])
    image = models.ImageField(upload_to="reports/%Y/%m/", blank=True)
    contact_method = models.CharField(max_length=5, choices=Contact.choices)
    contact_info = models.CharField(max_length=254)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
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
                RegexValidator(r"^\+?[0-9 ()-]{7,25}$", "Enter a valid phone number.")(self.contact_info)
        except ValidationError as exc:
            raise ValidationError({"contact_info": exc.messages})

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
    created_at = models.DateTimeField(auto_now_add=True)


class SubmissionWindow(models.Model):
    # HMAC of the client IP; no raw network address is retained.
    key = models.CharField(max_length=64, primary_key=True)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    count = models.PositiveIntegerField(default=0)
