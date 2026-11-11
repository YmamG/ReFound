from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings


@override_settings(LANGUAGE_CODE='en')
class PublicPageTests(TestCase):
    def test_home_page_uses_shared_navigation(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertContains(response, 'ReFound')
        self.assertContains(response, 'href="/about/"')
        self.assertContains(response, 'href="/contact/"')

    def test_placeholder_pages_load(self):
        for path, template in (
            ('/about/', 'core/about.html'),
            ('/contact/', 'core/contact.html'),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
                self.assertTemplateUsed(response, 'base.html')

    def test_project_stylesheet_is_discoverable(self):
        self.assertIsNotNone(finders.find('css/style.css'))

from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .forms import ReportForm
from .models import Report, Claim, AbuseReport, SubmissionWindow
from .services.matching import potential_matches, score_pair


def report_data(**changes):
    data = dict(title='Blue laptop bag', description='A blue laptop bag with a fabric strap.', category='bags', building='students', color='blue', location='Campus library', event_date=timezone.localdate().isoformat(), contact_method='email', contact_info='private@example.com')
    data.update(changes)
    return data


def make_report(**changes):
    data = report_data()
    data.update(kind='lost', management_hash=make_password('test-owner-key'))
    data.update(changes)
    if isinstance(data["event_date"], str):
        from datetime import date
        data["event_date"] = date.fromisoformat(data["event_date"])
    return Report.objects.create(**data)


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False, LANGUAGE_CODE='en')
class MVPTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.media.cleanup)
        self.addCleanup(self.settings_override.disable)

    def post_report(self, kind, data):
        url = reverse("core:submit", args=[kind])
        nonce = self.client.get(url).context["submission_id"]
        return self.client.post(url, {**data, "submission_id": nonce})

    def url(self, name, report):
        return reverse('core:' + name, args=[report.pk])

    def unlock(self, report, client=None):
        return (client or self.client).post(self.url('manage', report), {'action': 'unlock', 'token': 'test-owner-key'})

    def test_both_submission_workflows_use_private_device_ownership(self):
        for kind in ('lost', 'found'):
            response = self.post_report(kind, report_data())
            self.assertEqual(response.status_code, 302)
            report = Report.objects.get(kind=kind)
            self.assertIsNotNone(report.owner_id)
            from django.contrib.auth.hashers import is_password_usable
            self.assertFalse(is_password_usable(report.management_hash))
            self.assertNotIn(self.client.cookies['refound_device'].value, str(dict(self.client.session)))
            self.assertIn('no-store', response['Cache-Control'])
            for name in ('detail', 'matches', 'manage'):
                page = self.client.get(self.url(name, report))
                self.assertNotContains(page, 'private@example.com')
                self.assertNotContains(page, self.client.cookies['refound_device'].value)
            self.assertNotContains(self.client.get(reverse('core:browse')), 'private@example.com')

    def test_model_validation(self):
        report = make_report()
        report.full_clean()
        report.event_date = timezone.localdate() + timedelta(days=1)
        with self.assertRaises(ValidationError):
            report.full_clean()
        report.event_date = timezone.localdate()
        report.kind = 'invalid'
        with self.assertRaises(ValidationError):
            report.full_clean()

    def test_invalid_forms_do_not_save(self):
        for changes in ({'event_date': (timezone.localdate() + timedelta(days=1)).isoformat()}, {'title': 'x'}, {'category': 'invalid'}, {'contact_info': 'bad email'}, {'contact_method': 'phone', 'contact_info': 'abc'}, {'website': 'spam.example'}):
            response = self.post_report('lost', report_data(**changes))
            self.assertTrue(response.context['form'].errors)
        self.assertEqual(Report.objects.count(), 0)

    def test_phone_contact_accepted(self):
        self.assertTrue(ReportForm(data=report_data(contact_method='phone', contact_info='+966 555 123456')).is_valid())

    def test_upload_sanitized_and_served_as_image(self):
        image = Image.new('RGB', (32, 32), 'blue')
        output = BytesIO()
        image.save(output, format='PNG')
        upload = SimpleUploadedFile('unsafe-name.png', output.getvalue() + b'<script>bad</script>', content_type='image/png')
        response = self.post_report('found', report_data(image=upload))
        self.assertEqual(response.status_code, 302)
        report = Report.objects.get()
        self.assertTrue(report.image.name.endswith('.jpg'))
        self.assertNotIn('unsafe-name', report.image.name)
        with report.image.open('rb') as file:
            data = file.read()
        self.assertNotIn(b'<script>', data)
        photo = self.client.get(self.url('image', report))
        self.assertEqual(photo['Content-Type'], 'image/jpeg')
        self.assertEqual(photo['X-Content-Type-Options'], 'nosniff')
        photo.close()

    def test_invalid_upload_rejected(self):
        for name, content in [('x.svg', b'<svg></svg>'), ('x.jpg', b'not an image')]:
            form = ReportForm(data=report_data(), files={'image': SimpleUploadedFile(name, content)})
            self.assertFalse(form.is_valid())
            self.assertIn('image', form.errors)

    def test_oversized_image_rejected(self):
        output = BytesIO()
        Image.new('RGB', (10, 10)).save(output, format='PNG')
        upload = SimpleUploadedFile('large.png', output.getvalue() + b'0' * (5 * 1024 * 1024))
        form = ReportForm(data=report_data(), files={'image': upload})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_combined_filters_and_pagination_preserve_query(self):
        for _ in range(13):
            make_report(kind='found')
        make_report(kind='lost')
        make_report(kind='found', category='keys')
        response = self.client.get(reverse('core:browse'), {'q': 'laptop', 'kind': 'found', 'category': 'bags', 'location': 'library', 'status': 'active', 'sort': 'oldest'})
        self.assertEqual(response.context['page_obj'].paginator.count, 13)
        self.assertEqual(len(response.context['page_obj']), 12)
        self.assertContains(response, 'category=bags')
        self.assertContains(response, 'page=2')
        page = self.client.get(reverse('core:browse'), {'kind': 'found', 'category': 'bags', 'page': 2})
        self.assertEqual(len(page.context['page_obj']), 1)
        ordered = list(response.context['page_obj'])
        self.assertLessEqual(ordered[0].created_at, ordered[-1].created_at)
        self.assertEqual(self.client.get(reverse('core:browse'), {'q': 'missing'}).context['page_obj'].paginator.count, 0)

    def test_owner_access_status_and_lock(self):
        report = make_report()
        self.assertEqual(self.client.post(self.url('manage', report), {'action': 'status', 'status': 'resolved'}).status_code, 403)
        self.assertEqual(self.unlock(report).status_code, 302)
        self.client.post(self.url('manage', report), {'action': 'status', 'status': 'matched'})
        report.refresh_from_db()
        self.assertEqual(report.status, 'matched')
        response = self.client.post(self.url('manage', report), {'action': 'status', 'status': 'bogus'})
        self.assertContains(response, 'Select a valid choice')
        self.client.post(self.url('manage', report), {'action': 'lock'})
        self.assertEqual(self.client.post(self.url('manage', report), {'action': 'delete'}).status_code, 403)

    def test_wrong_key_and_other_report_do_not_authorize(self):
        report = make_report()
        other = make_report()
        self.client.post(self.url('manage', report), {'action': 'unlock', 'token': 'wrong'})
        self.assertNotIn('manage_' + str(report.pk), self.client.session)
        self.unlock(report)
        self.assertEqual(self.client.post(self.url('manage', other), {'action': 'delete'}).status_code, 403)
        self.assertNotContains(Client().get(self.url('manage', report)), 'Private messages')

    def test_claim_inbox_private_and_owner_can_read(self):
        report = make_report()
        response = self.client.post(self.url('claim', report), {'message': 'The inside pocket has a red label.', 'reply_email': 'claimant@example.com'}, follow=True)
        self.assertContains(response, 'Message saved privately')
        self.assertEqual(Claim.objects.count(), 1)
        self.assertNotContains(self.client.get(self.url('manage', report)), 'claimant@example.com')
        self.assertNotContains(self.client.get(self.url('detail', report)), 'red label')
        self.unlock(report)
        response = self.client.get(self.url('manage', report))
        self.assertContains(response, 'claimant@example.com')
        self.assertContains(response, 'red label')
        report.status = 'resolved'
        report.save()
        self.assertEqual(self.client.post(self.url('claim', report), {'message': 'hello there', 'reply_email': 'x@example.com'}).status_code, 410)

    def test_invalid_claim_and_abuse(self):
        report = make_report()
        response = self.client.post(self.url('claim', report), {'message': 'x', 'reply_email': 'invalid'})
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(Claim.objects.count(), 0)
        self.client.post(self.url('abuse', report), {'reason': 'Contains private personal information.'})
        self.assertEqual(AbuseReport.objects.count(), 1)
        self.assertNotContains(self.client.get(self.url('detail', report)), 'Contains private personal information')

    def test_delete_requires_post_and_deletes_related_data(self):
        report = make_report()
        Claim.objects.create(report=report, message='A private claim', reply_email='x@example.com')
        self.unlock(report)
        self.client.get(self.url('manage', report), {'action': 'delete'})
        self.assertTrue(Report.objects.filter(pk=report.pk).exists())
        self.assertEqual(self.client.post(self.url('manage', report), {'action': 'delete'}).status_code, 400)
        self.client.post(self.url('manage', report), {'action': 'delete', 'confirm_delete': 'yes'})
        self.assertFalse(Report.objects.filter(pk=report.pk).exists())
        self.assertEqual(Claim.objects.count(), 0)

    def test_csrf_enforced(self):
        report = make_report()
        client = Client(enforce_csrf_checks=True)
        for url in [reverse('core:submit', args=['lost']), self.url('manage', report), self.url('claim', report), self.url('abuse', report)]:
            self.assertEqual(client.post(url, {}).status_code, 403)

    def test_rate_limit_shared_across_sessions_and_expires(self):
        url = reverse('core:submit', args=['lost'])
        for _ in range(10):
            self.assertEqual(Client().post(url, {}).status_code, 400)
        self.assertEqual(Client().post(url, {}).status_code, 429)
        SubmissionWindow.objects.update(started_at=timezone.now() - timedelta(minutes=11))
        self.assertEqual(Client().post(url, {}).status_code, 400)

    def test_public_user_input_escaped_and_unknown_routes(self):
        report = make_report(title='<script>alert(1)</script>')
        page = self.client.get(self.url('detail', report))
        self.assertNotContains(page, '<script>alert(1)</script>')
        self.assertContains(page, '&lt;script&gt;')
        self.assertEqual(self.client.get(reverse('core:submit', args=['invalid'])).status_code, 404)
        self.assertEqual(self.client.get(self.url('image', report)).status_code, 404)

    def test_matching_opposite_types_and_explanations(self):
        lost = make_report()
        found = make_report(kind='found')
        make_report(kind='lost')
        make_report(kind='found', status='resolved')
        matches = potential_matches(lost)
        self.assertEqual([m.report.pk for m in matches], [found.pk])
        self.assertEqual(matches[0].score, 100)
        self.assertEqual(len(matches[0].reasons), 5)
        self.assertEqual(score_pair(lost, lost), (0, ()))
        self.assertContains(self.client.get(self.url('matches', lost)), 'Same category')

    def test_matching_threshold_dates_and_resolved(self):
        lost = make_report()
        found = make_report(kind='found', title='Wallet', description='Leather wallet with many compartments', category='other', color='red', location='Sports center', event_date=timezone.localdate() - timedelta(days=60))
        self.assertEqual(score_pair(lost, found), (0, ()))
        self.assertEqual(potential_matches(lost), [])
        lost.status = 'resolved'
        self.assertEqual(potential_matches(lost), [])
