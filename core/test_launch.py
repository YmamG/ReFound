"""Regression coverage for the real-user-testing MVP; no research dependencies."""
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import OwnerLookupForm, ReportForm
from .models import AbuseReport, Claim, Report, SubmissionWindow
from .services.matching import potential_matches
from .services.security import allow_submission, client_address
from .tests import make_report, report_data


def photo_bytes(mode='RGB', size=(32, 32)):
    output = BytesIO()
    Image.new(mode, size).save(output, format='PNG')
    return output.getvalue()


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class LaunchWorkflowTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)

    def url(self, name, report):
        return reverse('core:' + name, args=[report.pk])

    def unlock(self, report, client=None):
        return (client or self.client).post(self.url('manage', report), {'action': 'unlock', 'token': 'test-owner-key'})

    def with_photo(self, **kwargs):
        report = make_report(**kwargs)
        report.image.save('test.jpg', ContentFile(photo_bytes()), save=True)
        return report

    def test_submission_refresh_creates_one_report_and_does_not_redisplay_key(self):
        url = reverse('core:submit', args=['lost'])
        nonce = self.client.get(url).context['submission_id']
        data = {**report_data(), 'submission_id': nonce}
        response = self.client.post(url, data)
        key = response.context['token']
        report = Report.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(key, str(dict(self.client.session)))
        repeated = self.client.post(url, data)
        self.assertRedirects(repeated, self.url('manage', report))
        self.assertEqual(Report.objects.count(), 1)
        self.assertNotContains(self.client.get(self.url('manage', report)), key)
        self.assertContains(self.client.get(self.url('manage', report)), 'Private messages')

    def test_stale_form_preserves_details_and_can_be_resubmitted(self):
        url = reverse('core:submit', args=['found'])
        response = self.client.post(url, report_data())
        self.assertContains(response, 'form has expired', status_code=400)
        self.assertContains(response, 'Blue laptop bag', status_code=400)
        self.assertEqual(Report.objects.count(), 0)
        data = {**report_data(), 'submission_id': response.context['submission_id']}
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(Report.objects.count(), 1)

    def test_pending_form_storage_is_bounded(self):
        for _ in range(16):
            self.client.get(reverse('core:submit', args=['lost']))
        self.assertEqual(len(self.client.session['report_forms']), 12)

    def test_public_post_routes_require_csrf_even_with_valid_session(self):
        client = Client(enforce_csrf_checks=True)
        url = reverse('core:submit', args=['lost'])
        nonce = client.get(url).context['submission_id']
        denied = client.post(url, {**report_data(), 'submission_id': nonce})
        self.assertContains(denied, 'Reload the form', status_code=403)
        self.assertEqual(Report.objects.count(), 0)
        response = client.post(url, {**report_data(), 'submission_id': nonce}, HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Report.objects.count(), 1)

    def test_owner_lookup_accepts_id_and_management_or_public_link(self):
        report = make_report()
        for value in [str(report.pk), 'https://example.org' + self.url('detail', report), self.url('manage', report)]:
            client = Client()
            response = client.post(reverse('core:owner_lookup'), {'report_link': value, 'token': 'test-owner-key'})
            self.assertRedirects(response, self.url('manage', report))
            self.assertContains(client.get(self.url('manage', report)), 'Private messages')

    def test_malformed_owner_lookup_never_fetches_url_or_crashes(self):
        for value in ['http://[invalid', 'garbage', 'https://example.org/reports/not-a-uuid/', '/reports/zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz/']:
            form = OwnerLookupForm({'report_link': value, 'token': 'anything'})
            self.assertFalse(form.is_valid())
            self.assertIn('report_link', form.errors)

    def test_expired_grant_is_not_extended_by_unlocking_another_report(self):
        first, second = make_report(), make_report()
        self.unlock(first)
        session = self.client.session
        grant = session['manage_' + str(first.pk)]
        grant['expires'] = int(timezone.now().timestamp()) - 1
        session['manage_' + str(first.pk)] = grant
        session.save()
        self.unlock(second)
        self.assertNotContains(self.client.get(self.url('manage', first)), 'Private messages')
        self.assertContains(self.client.get(self.url('manage', second)), 'Private messages')

    def test_changed_hash_revokes_grant_and_legacy_boolean_is_not_access(self):
        report = make_report()
        self.unlock(report)
        report.management_hash = make_password('replacement-key')
        report.save()
        self.assertNotContains(self.client.get(self.url('manage', report)), 'Private messages')
        session = self.client.session
        session['manage_' + str(report.pk)] = True
        session.save()
        self.assertEqual(self.client.post(self.url('manage', report), {'action': 'delete', 'confirm_delete': 'yes'}).status_code, 403)
        self.assertTrue(Report.objects.filter(pk=report.pk).exists())

    def test_lock_is_available_after_public_rate_limit_exhausted(self):
        report = make_report()
        self.unlock(report)
        SubmissionWindow.objects.update(count=10)
        self.assertEqual(self.client.post(self.url('manage', report), {'action': 'lock'}).status_code, 302)
        self.assertNotContains(self.client.get(self.url('manage', report)), 'Private messages')

    def test_private_owner_page_does_not_disclose_title_or_inbox(self):
        report = make_report(title='Private ownership title')
        Claim.objects.create(report=report, message='A private secret detail', reply_email='secret@example.com')
        response = self.client.get(self.url('manage', report))
        for value in ['Private ownership title', 'A private secret detail', 'secret@example.com', report.management_hash]:
            self.assertNotContains(response, value)
        self.assertIn('no-store', response['Cache-Control'])

    def test_private_inbox_pagination_and_escaping(self):
        report = make_report()
        for _ in range(11):
            Claim.objects.create(report=report, message='<script>alert(1)</script>', reply_email='reply@example.com')
        self.unlock(report)
        response = self.client.get(self.url('manage', report))
        self.assertEqual(len(response.context['inbox']), 10)
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;')
        self.assertEqual(len(self.client.get(self.url('manage', report), {'page': 2}).context['inbox']), 1)

    def test_message_and_abuse_use_redirect_and_refresh_does_not_resubmit(self):
        report = make_report()
        for name, data, model in [('claim', {'message': 'The lining has a blue label.', 'reply_email': 'reply@example.com'}, Claim), ('abuse', {'reason': 'This contains personal information.'}, AbuseReport)]:
            response = self.client.post(self.url(name, report), data)
            self.assertRedirects(response, self.url('detail', report))
            self.client.get(response.url)
            self.assertEqual(model.objects.count(), 1)
        page = self.client.get(self.url('detail', report))
        self.assertNotContains(page, 'blue label')
        self.assertNotContains(page, 'reply@example.com')
        self.assertNotContains(page, 'personal information')

    def test_hidden_reports_excluded_from_all_public_entry_points(self):
        hidden = self.with_photo(kind='found', title='Hidden special backpack', is_hidden=True)
        visible = make_report()
        for path in ['/', reverse('core:browse')]:
            self.assertNotContains(self.client.get(path), hidden.title)
        self.assertEqual(potential_matches(visible), [])
        self.assertEqual(potential_matches(hidden), [])
        for name in ['detail', 'matches', 'image', 'claim', 'abuse']:
            self.assertEqual(self.client.get(self.url(name, hidden)).status_code, 404)
        self.assertEqual(self.client.post(self.url('claim', hidden), {'message': 'This must not be saved', 'reply_email': 'x@example.com'}).status_code, 404)
        self.assertEqual(Claim.objects.count(), 0)
        self.unlock(hidden)
        self.assertContains(self.client.get(self.url('manage', hidden)), 'hidden from public pages')
        image = self.client.get(self.url('image', hidden))
        self.assertEqual(image.status_code, 200)
        image.close()

    def test_hidden_photos_require_owner_or_specific_admin_permission(self):
        report = self.with_photo(is_hidden=True)
        user = get_user_model().objects.create_user(username='moderator', password='A-secure-test-password')
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url('image', report)).status_code, 404)
        user.user_permissions.add(Permission.objects.get(codename='view_report'))
        image = self.client.get(self.url('image', report))
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image['Content-Security-Policy'], "default-src 'none'; sandbox")
        self.assertIn('no-store', image['Cache-Control'])
        image.close()

    def test_owner_deletion_removes_photo_after_commit(self):
        report = self.with_photo()
        filename = Path(report.image.path)
        self.unlock(report)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url('manage', report), {'action': 'delete', 'confirm_delete': 'yes'})
            self.assertTrue(filename.exists())
        self.assertEqual(response.status_code, 302)
        self.assertFalse(filename.exists())
        self.assertEqual(Report.objects.count(), 0)

    def test_queryset_deletion_cleans_photos_but_rollback_preserves_them(self):
        report = self.with_photo()
        filename, pk = Path(report.image.path), report.pk
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    Report.objects.filter(pk=pk).delete()
                    raise ValueError('rollback')
            except ValueError:
                pass
        self.assertTrue(filename.exists())
        self.assertTrue(Report.objects.filter(pk=pk).exists())
        with self.captureOnCommitCallbacks(execute=True):
            Report.objects.filter(pk=pk).delete()
        self.assertFalse(filename.exists())

    def test_missing_stored_photo_is_404(self):
        report = self.with_photo()
        Path(report.image.path).unlink()
        self.assertEqual(self.client.get(self.url('image', report)).status_code, 404)

    def test_large_request_is_rejected_before_csrf_or_database_write(self):
        client = Client(enforce_csrf_checks=True)
        response = client.generic('POST', reverse('core:submit', args=['lost']), b'x' * (6 * 1024 * 1024 + 1), content_type='application/octet-stream')
        self.assertContains(response, 'upload is a little too large', status_code=413)
        self.assertEqual(Report.objects.count(), 0)

    def test_file_limit_aborts_before_image_is_saved(self):
        url = reverse('core:submit', args=['lost'])
        nonce = self.client.get(url).context['submission_id']
        upload = SimpleUploadedFile('oversize.png', photo_bytes() + b'0' * (5 * 1024 * 1024), content_type='image/png')
        response = self.client.post(url, {**report_data(), 'submission_id': nonce, 'image': upload})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(Report.objects.count(), 0)

    def test_oversized_attachment_cannot_save_a_message_or_abuse_report(self):
        report = make_report()
        for route, data, model in [('claim', {'message': 'This must not be saved.', 'reply_email': 'x@example.com'}, Claim), ('abuse', {'reason': 'This must not be saved.'}, AbuseReport)]:
            upload = SimpleUploadedFile('large.png', b'x' * (5 * 1024 * 1024 + 1))
            response = self.client.post(self.url(route, report), {**data, 'image': upload})
            self.assertEqual(response.status_code, 413)
            self.assertEqual(model.objects.count(), 0)

    def test_multiple_uploads_are_rejected_before_report_creation(self):
        url = reverse('core:submit', args=['lost'])
        nonce = self.client.get(url).context['submission_id']
        uploads = [SimpleUploadedFile('one.png', photo_bytes()), SimpleUploadedFile('two.png', photo_bytes())]
        response = self.client.post(url, {**report_data(), 'submission_id': nonce, 'image': uploads})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Report.objects.count(), 0)

    def test_transparent_png_is_flattened_and_large_dimensions_rejected(self):
        form = ReportForm(report_data(), {'image': SimpleUploadedFile('alpha.png', photo_bytes('RGBA'))})
        self.assertTrue(form.is_valid(), form.errors)
        with Image.open(form.cleaned_data['image']) as image:
            self.assertEqual(image.mode, 'RGB')
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
        form = ReportForm(report_data(), {'image': SimpleUploadedFile('big.png', photo_bytes(size=(4001, 3000)))})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_animated_png_is_rejected(self):
        output = BytesIO()
        Image.new('RGB', (20, 20), 'red').save(output, format='PNG', save_all=True, append_images=[Image.new('RGB', (20, 20), 'blue')], duration=100)
        form = ReportForm(report_data(), {'image': SimpleUploadedFile('animation.png', output.getvalue())})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_exif_orientation_is_applied_and_metadata_stripped(self):
        output = BytesIO()
        image = Image.new('RGB', (30, 10), 'blue')
        exif = Image.Exif()
        exif[274] = 6
        exif[270] = 'private identifying metadata'
        image.save(output, format='JPEG', exif=exif)
        form = ReportForm(report_data(), {'image': SimpleUploadedFile('test.jpg', output.getvalue())})
        self.assertTrue(form.is_valid(), form.errors)
        with Image.open(form.cleaned_data['image']) as sanitized:
            self.assertEqual(sanitized.size, (10, 30))
            self.assertFalse(sanitized.getexif())

    def test_invalid_filters_are_accessible_errors_not_server_errors(self):
        make_report()
        response = self.client.get(reverse('core:browse'), {'kind': 'anything', 'q': 'x' * 201})
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertEqual(response.context['page_obj'].paginator.count, 0)

    def test_read_only_routes_reject_post_and_unknown_page_numbers_are_safe(self):
        report = make_report()
        for path in ['/', reverse('core:browse'), self.url('detail', report), self.url('image', report), self.url('matches', report)]:
            self.assertEqual(self.client.post(path, {}).status_code, 405)
        for page in ['nonsense', '-1', '999']:
            self.assertEqual(self.client.get(reverse('core:browse'), {'page': page}).status_code, 200)

    @override_settings(DEBUG=False)
    def test_error_pages_and_public_headers_do_not_expose_internal_details(self):
        response = self.client.get('/nonexistent/')
        self.assertContains(response, 'A little lost?', status_code=404)
        self.assertNotContains(response, 'urlpatterns', status_code=404)
        self.assertIn("script-src 'self'", response['Content-Security-Policy'])
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        from .views import server_error
        response = server_error(RequestFactory().get('/'))
        self.assertContains(response, 'small detour', status_code=500)

    def test_moderation_admin_can_hide_restore_and_mark_reviewed(self):
        report = make_report()
        concern = AbuseReport.objects.create(report=report, reason='Review this report')
        moderator = get_user_model().objects.create_superuser('administrator', 'admin@example.com', 'A-secure-test-password')
        self.client.force_login(moderator)
        changelist = reverse('admin:core_report_changelist')
        for action, hidden in [('hide_reports', True), ('restore_reports', False)]:
            response = self.client.post(changelist, {'action': action, '_selected_action': str(report.pk)})
            self.assertEqual(response.status_code, 302)
            report.refresh_from_db()
            self.assertEqual(report.is_hidden, hidden)
        self.client.post(reverse('admin:core_abusereport_changelist'), {'action': 'mark_reviewed', '_selected_action': concern.pk})
        concern.refresh_from_db()
        self.assertTrue(concern.reviewed)
        response = self.client.get(reverse('admin:core_report_change', args=[report.pk]))
        self.assertNotContains(response, report.management_hash)
        self.assertNotContains(response, 'type="file"')


class NetworkBoundaryTests(TestCase):
    def test_untrusted_proxy_header_cannot_bypass_rate_limit(self):
        request = RequestFactory().post('/', REMOTE_ADDR='198.51.100.5', HTTP_X_FORWARDED_FOR='192.0.2.10')
        self.assertEqual(client_address(request), '198.51.100.5')
        with override_settings(REFOUND_RATE_LIMIT=1):
            self.assertTrue(allow_submission(request))
            request.META['HTTP_X_FORWARDED_FOR'] = '192.0.2.11'
            self.assertFalse(allow_submission(request))
        self.assertNotIn('198.51.100.5', SubmissionWindow.objects.get().key)

    @override_settings(REFOUND_TRUSTED_PROXY_CIDRS=['10.0.0.0/8', '2001:db8:1::/48'])
    def test_proxy_chain_walks_from_trusted_edge_to_first_untrusted_hop(self):
        request = RequestFactory().get('/', REMOTE_ADDR='10.0.0.2', HTTP_X_FORWARDED_FOR='192.0.2.99, 198.51.100.8, 10.1.2.3')
        self.assertEqual(client_address(request), '198.51.100.8')
        request.META['HTTP_X_FORWARDED_FOR'] = 'invalid'
        self.assertEqual(client_address(request), '10.0.0.2')
        request.META['REMOTE_ADDR'] = 'invalid'
        self.assertEqual(client_address(request), 'unknown')

    @override_settings(REFOUND_RATE_LIMIT=1)
    def test_admin_login_has_separate_shared_rate_limit(self):
        response = self.client.post('/admin/login/', {'username': 'nobody', 'password': 'bad'})
        self.assertEqual(response.status_code, 200)
        response = Client().post('/admin/login/', {'username': 'nobody', 'password': 'bad'})
        self.assertContains(response, 'Too many sign-in attempts', status_code=429)
        self.assertEqual(response['Retry-After'], '600')
        self.assertEqual(self.client.post(reverse('core:submit', args=['lost']), {}).status_code, 400)
