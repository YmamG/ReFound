from io import BytesIO
from uuid import uuid4
import warnings

from PIL import Image, ImageOps
from django import forms
from django.utils import timezone
from urllib.parse import urlsplit
import re
import uuid
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event_date'].widget.attrs['max'] = timezone.localdate().isoformat()
        self.fields['image'].widget.attrs.update({'accept': 'image/jpeg,image/png', 'data-photo-input': ''})
        self.fields['contact_info'].widget.attrs['autocomplete'] = 'off'

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
                    if getattr(source, 'n_frames', 1) != 1:
                        raise ValueError('Use a still image')
                    source.load()
                    oriented = ImageOps.exif_transpose(source)
                    if oriented.mode in {'RGBA', 'LA'} or 'transparency' in oriented.info:
                        rgba = oriented.convert('RGBA')
                        clean = Image.new('RGB', rgba.size, 'white')
                        clean.paste(rgba, mask=rgba.getchannel('A'))
                    else:
                        clean = oriented.convert('RGB')
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


class BrowseForm(forms.Form):
    q = forms.CharField(required=False, max_length=200, label='Search belongings', widget=forms.TextInput(attrs={'placeholder': 'What are you looking for?', 'type': 'search'}))
    kind = forms.ChoiceField(required=False, label='Report type', choices=[('', 'Lost & found'), *Report.Kind.choices])
    category = forms.ChoiceField(required=False, choices=[('', 'All categories'), *Report.Category.choices])
    location = forms.CharField(required=False, max_length=120, label='General area', widget=forms.TextInput(attrs={'placeholder': 'e.g. Campus library'}))
    status = forms.ChoiceField(required=False, choices=[('', 'All statuses'), *Report.Status.choices])
    sort = forms.ChoiceField(required=False, label='Sort by', choices=[('newest', 'Newest first'), ('oldest', 'Oldest first')])


class OwnerLookupForm(ManagementForm):
    report_link = forms.CharField(max_length=500, label='Report link or ID', widget=forms.TextInput(attrs={'placeholder': 'Paste your report link or ID', 'autocomplete': 'off'}))

    def clean_report_link(self):
        value = self.cleaned_data['report_link'].strip()
        try:
            return uuid.UUID(value)
        except ValueError:
            try:
                path = urlsplit(value).path
            except ValueError:
                raise forms.ValidationError('Paste a valid ReFound report link or report ID.')
            match = re.fullmatch(r'/reports/([0-9a-fA-F-]{36})/(?:manage/)?', path)
            if not match:
                raise forms.ValidationError('Paste a valid ReFound report link or report ID.')
            try:
                return uuid.UUID(match.group(1))
            except ValueError:
                raise forms.ValidationError('Enter a valid report ID.')
