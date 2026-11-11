from django.utils.translation import gettext_lazy as _
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.label = _(str(field.label or name.replace('_', ' ').capitalize()))

    website = forms.CharField(required=False, label=_("Leave this field empty"), widget=forms.HiddenInput)

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError(_("Unable to accept this submission."))
        return ""


class ReportForm(SpamProtectedForm, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['building'].required = True
        self.fields['building'].choices = [('', _('Choose a building')), *Report.Building.choices]
        self.fields['classroom'].label = _('Classroom / lab number')
        self.fields['location'].help_text = _('Area inside the College of Computing, e.g. library or first-floor corridor.')
        self.fields['event_date'].widget.attrs['max'] = timezone.localdate().isoformat()
        self.fields['image'].widget.attrs.update({'accept': 'image/jpeg,image/png', 'data-photo-input': ''})
        self.fields['contact_info'].widget.attrs['autocomplete'] = 'off'

    class Meta:
        model = Report
        fields = ["title", "description", "category", "color", "building", "location", "classroom", "event_date", "image", "contact_method", "contact_info"]
        widgets = {"event_date": forms.DateInput(attrs={"type": "date"}), "description": forms.Textarea(attrs={"rows": 5})}
        help_texts = {"description": _("Do not include contact details, exact locations, or unique ownership evidence in public text."), "contact_info": _("Private: visible only to authorized site administrators."), "image": _("JPEG or PNG, up to 5 MB and 12 million pixels. Avoid faces, IDs and identifying details.")}

    def clean_contact_info(self):
        value = self.cleaned_data["contact_info"].strip()
        if self.cleaned_data.get("contact_method") == Report.Contact.EMAIL:
            validate_email(value)
        elif self.cleaned_data.get("contact_method") == Report.Contact.PHONE:
            RegexValidator(r"^\+?[0-9 ()-]{7,25}$", _("Enter a valid phone number."))(value)
        return value

    def clean_image(self):
        upload = self.cleaned_data.get("image")
        if not upload:
            return upload
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError(_("Image must be no larger than 5 MB."))
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
            raise forms.ValidationError(_("Upload a valid JPEG or PNG image within the size limits."))


class ClaimForm(SpamProtectedForm, forms.ModelForm):
    class Meta:
        model = Claim
        fields = ["message", "reply_email"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}
        help_texts = {"message": _("Describe evidence of ownership privately. Do not send passwords or sensitive documents."), "reply_email": _("Shared privately with the report owner so they can reply.")}

    def clean_message(self):
        value = self.cleaned_data["message"]
        if len(value) < 10:
            raise forms.ValidationError(_("Please provide at least 10 characters."))
        return value


class AbuseForm(SpamProtectedForm, forms.ModelForm):
    class Meta:
        model = AbuseReport
        fields = ["reason"]


class ManagementForm(forms.Form):
    token = forms.CharField(max_length=200, widget=forms.PasswordInput, label=_("Management key"))


class StatusForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["status"]
        labels = {"status": _("Status")}


class BrowseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.label = _(str(field.label or name.replace('_', ' ').capitalize()))

    color = forms.CharField(required=False, max_length=50, label=_('Color'))

    building = forms.ChoiceField(required=False, choices=[('', _('Both buildings')), *Report.Building.choices])
    q = forms.CharField(required=False, max_length=200, label=_('Search belongings'), widget=forms.TextInput(attrs={'placeholder': _('What are you looking for?'), 'type': 'search'}))
    kind = forms.ChoiceField(required=False, label=_('Report type'), choices=[('', _('Lost & found')), *Report.Kind.choices])
    category = forms.ChoiceField(required=False, choices=[('', _('All categories')), *Report.Category.choices])
    location = forms.CharField(required=False, max_length=120, label=_('General area'), widget=forms.TextInput(attrs={'placeholder': _('e.g. Campus library')}))
    status = forms.ChoiceField(required=False, choices=[('', _('All statuses')), *Report.Status.choices])
    sort = forms.ChoiceField(required=False, label=_('Sort by'), choices=[('newest', _('Newest first')), ('oldest', _('Oldest first'))])


class OwnerLookupForm(ManagementForm):
    report_link = forms.CharField(max_length=500, label=_('Report link or ID'), widget=forms.TextInput(attrs={'placeholder': _('Paste your report link or ID'), 'autocomplete': 'off'}))

    def clean_report_link(self):
        value = self.cleaned_data['report_link'].strip()
        try:
            return uuid.UUID(value)
        except ValueError:
            try:
                path = urlsplit(value).path
            except ValueError:
                raise forms.ValidationError(_('Paste a valid ReFound report link or report ID.'))
            match = re.fullmatch(r'/reports/([0-9a-fA-F-]{36})/(?:manage/)?', path)
            if not match:
                raise forms.ValidationError(_('Paste a valid ReFound report link or report ID.'))
            try:
                return uuid.UUID(match.group(1))
            except ValueError:
                raise forms.ValidationError(_('Enter a valid report ID.'))
