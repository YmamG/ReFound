from io import BytesIO
from uuid import uuid4
import warnings

from PIL import Image, ImageOps
from django import forms
from django.core.files.base import ContentFile
from django.core.validators import validate_email, RegexValidator

from .models import Report, Claim, AbuseReport


class SpamProtectedForm(forms.Form):
    website = forms.CharField(required=False, label="Leave this field empty", widget=forms.HiddenInput)

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Unable to accept this submission.")
        return ""


class ReportForm(SpamProtectedForm, forms.ModelForm):
    class Meta:
        model = Report
        fields = ["title", "description", "category", "color", "location", "event_date", "image", "contact_method", "contact_info"]
        widgets = {"event_date": forms.DateInput(attrs={"type": "date"}), "description": forms.Textarea(attrs={"rows": 5})}
        help_texts = {"description": "Do not include contact details, exact locations, or unique ownership evidence in public text.", "contact_info": "Private: visible only to authorized site administrators.", "image": "JPEG or PNG, up to 5 MB and 12 million pixels. Avoid faces, IDs and identifying details."}

    def clean_contact_info(self):
        value = self.cleaned_data["contact_info"].strip()
        if self.cleaned_data.get("contact_method") == Report.Contact.EMAIL:
            validate_email(value)
        elif self.cleaned_data.get("contact_method") == Report.Contact.PHONE:
            RegexValidator(r"^\+?[0-9 ()-]{7,25}$", "Enter a valid phone number.")(value)
        return value

    def clean_image(self):
        upload = self.cleaned_data.get("image")
        if not upload:
            return upload
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Image must be no larger than 5 MB.")
        try:
            upload.seek(0)
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(upload) as source:
                    if source.format not in {"JPEG", "PNG"} or source.width * source.height > 12_000_000:
                        raise ValueError("Unsupported image")
                    source.load()
                    clean = ImageOps.exif_transpose(source).convert("RGB")
                    clean.thumbnail((1600, 1600))
                    out = BytesIO()
                    clean.save(out, format="JPEG", quality=85)
            # Decode/re-encode: discard original filename, metadata, animation and appended payloads.
            return ContentFile(out.getvalue(), name=f"{uuid4().hex}.jpg")
        except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise forms.ValidationError("Upload a valid JPEG or PNG image within the size limits.")


class ClaimForm(SpamProtectedForm, forms.ModelForm):
    class Meta:
        model = Claim
        fields = ["message", "reply_email"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}
        help_texts = {"message": "Describe evidence of ownership privately. Do not send passwords or sensitive documents.", "reply_email": "Shared privately with the report owner so they can reply."}

    def clean_message(self):
        value = self.cleaned_data["message"]
        if len(value) < 10:
            raise forms.ValidationError("Please provide at least 10 characters.")
        return value


class AbuseForm(SpamProtectedForm, forms.ModelForm):
    class Meta:
        model = AbuseReport
        fields = ["reason"]


class ManagementForm(forms.Form):
    token = forms.CharField(max_length=200, widget=forms.PasswordInput, label="Management key")


class StatusForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["status"]
