"""Browser identity, building separation and retention regression coverage."""
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Device, Report
from .services.matching import potential_matches, score_pair
from .tests import make_report, report_data


@override_settings(LANGUAGE_CODE='en', SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class CampusTests(TestCase):
    def submit(self, client=None, **changes):
        client = client or self.client
        url = reverse('core:submit', args=['lost'])
        nonce = client.get(url).context['submission_id']
        return client.post(url, {**report_data(**changes), 'submission_id': nonce})

    def test_same_browser_keeps_number_without_password_or_login(self):
        first = self.client.get('/')
        number = first.context['device_number']
        self.assertEqual(len(number), 8)
        self.assertTrue(number.isdigit())
        token = self.client.cookies[settings.REFOUND_DEVICE_COOKIE].value
        self.assertEqual(self.client.get('/').context['device_number'], number)
        self.assertEqual(Device.objects.count(), 1)
        self.assertNotEqual(Device.objects.get().credential_hash, token)
        self.assertNotContains(first, token)
        self.assertEqual(first.cookies[settings.REFOUND_DEVICE_COOKIE]['httponly'], True)
        self.assertEqual(first.cookies[settings.REFOUND_DEVICE_COOKIE]['samesite'], 'Lax')
        self.assertIn('Cookie', first['Vary'])
        self.assertIn('private', first['Cache-Control'])

    def test_number_alone_or_tampered_cookie_does_not_authorize(self):
        self.assertEqual(self.submit().status_code, 302)
        report = Report.objects.get()
        visitor = Client()
        visitor.cookies[settings.REFOUND_DEVICE_COOKIE] = report.owner.number
        response = visitor.get(reverse('core:manage', args=[report.pk]))
        self.assertNotContains(response, report.title)
        self.assertNotContains(response, 'Private messages')
        self.assertEqual(visitor.post(reverse('core:manage', args=[report.pk]), {'action': 'delete', 'confirm_delete': 'yes'}).status_code, 403)
        visitor.cookies[settings.REFOUND_DEVICE_COOKIE] = 'A' * 43
        self.assertEqual(visitor.post(reverse('core:manage', args=[report.pk]), {'action': 'status', 'status': 'resolved'}).status_code, 403)
        report.refresh_from_db()
        self.assertEqual(report.status, 'active')

    def test_my_reports_are_limited_to_this_browser_and_return_visit_works(self):
        self.submit()
        report = Report.objects.get()
        saved_cookie = self.client.cookies[settings.REFOUND_DEVICE_COOKIE].value
        self.assertContains(self.client.get(reverse('core:my_reports')), report.title)
        visitor = Client()
        self.assertNotContains(visitor.get(reverse('core:my_reports')), report.title)
        returning = Client()
        returning.cookies[settings.REFOUND_DEVICE_COOKIE] = saved_cookie
        self.assertContains(returning.get(reverse('core:my_reports')), report.title)
        self.assertContains(returning.get(reverse('core:manage', args=[report.pk])), 'Private messages')

    def test_deleting_cookies_creates_a_new_identity_and_revokes_access(self):
        self.submit()
        report = Report.objects.get()
        self.client.cookies.clear()
        page = self.client.get(reverse('core:my_reports'))
        self.assertNotEqual(page.context['device_number'], report.owner.number)
        self.assertNotContains(page, report.title)
        self.assertNotContains(self.client.get(reverse('core:manage', args=[report.pk])), 'Private messages')

    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_production_device_cookie_is_secure(self):
        response = self.client.get('/', secure=True)
        self.assertTrue(response.cookies[settings.REFOUND_DEVICE_COOKIE]['secure'])
        self.assertEqual(int(response.cookies[settings.REFOUND_DEVICE_COOKIE]['max-age']), 365 * 86400)

    def test_device_number_collision_retries_without_merging_browsers(self):
        first = self.client.get('/').context['device_number']
        with patch('core.models.secrets.randbelow', side_effect=[int(first) - 10_000_000, (int(first) - 10_000_000 + 1) % 90_000_000]):
            second = Client().get('/').context['device_number']
        self.assertNotEqual(first, second)
        self.assertEqual(Device.objects.count(), 2)

    def test_required_building_and_optional_classroom(self):
        self.assertEqual(self.submit(building='').status_code, 200)
        self.assertEqual(Report.objects.count(), 0)
        self.assertEqual(self.submit(building='women', classroom='A-204').status_code, 302)
        report = Report.objects.get()
        self.assertEqual(report.building, 'women')
        self.assertEqual(report.classroom, 'A-204')
        self.assertContains(self.client.get(reverse('core:detail', args=[report.pk])), 'A-204')

    def test_building_selection_sets_defaults_and_keeps_boards_separate(self):
        men = make_report(title='Men campus backpack', building='students')
        women = make_report(title='Women campus backpack', building='women')
        self.assertEqual(self.client.get(reverse('core:select_building')).status_code, 405)
        self.assertEqual(self.client.post(reverse('core:select_building'), {'building': 'unknown'}).status_code, 400)
        self.client.post(reverse('core:select_building'), {'building': 'women'})
        home = self.client.get('/')
        self.assertContains(home, women.title)
        self.assertNotContains(home, men.title)
        self.assertEqual(self.client.get(reverse('core:submit', args=['lost'])).context['form'].initial['building'], 'women')
        reports = self.client.get(reverse('core:browse')).context['page_obj']
        self.assertEqual([r.pk for r in reports], [women.pk])
        self.assertEqual(self.client.get(reverse('core:browse'), {'building': ''}).context['page_obj'].paginator.count, 2)

    def test_rule_match_respects_building_and_classroom_without_ai(self):
        report = make_report(building='women', classroom='A-204', location='First floor')
        wrong_building = make_report(kind='found', building='students', classroom='A-204')
        right = make_report(kind='found', building='women', classroom='A-204', location='Computing wing')
        self.assertEqual(score_pair(report, wrong_building), (0, ()))
        matches = potential_matches(report)
        self.assertEqual([m.report.pk for m in matches], [right.pk])
        self.assertEqual(matches[0].score, 100)
        self.assertIn('Same classroom', matches[0].reasons)

    def test_archive_is_automatic_at_sixty_days_and_keeps_detail_access(self):
        old = make_report(title='Old archive backpack')
        fresh = make_report(title='Fresh board backpack')
        Report.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=61))
        old.refresh_from_db()
        self.assertTrue(old.is_archived)
        self.assertFalse(fresh.is_archived)
        self.assertNotContains(self.client.get(reverse('core:browse')), old.title)
        self.assertContains(self.client.get(reverse('core:archive')), old.title)
        self.assertNotContains(self.client.get(reverse('core:archive')), fresh.title)
        self.assertContains(self.client.get(reverse('core:detail', args=[old.pk])), 'archived')
        self.assertEqual(self.client.post(reverse('core:claim', args=[old.pk]), {'message': 'Private new message', 'reply_email': 'reply@example.com'}).status_code, 410)
        self.assertEqual(potential_matches(old), [])

    def test_retention_preview_never_deletes_and_execute_only_deletes_after_a_year(self):
        expired = make_report()
        archived = make_report()
        Report.objects.filter(pk=expired.pk).update(created_at=timezone.now() - timedelta(days=366))
        Report.objects.filter(pk=archived.pk).update(created_at=timezone.now() - timedelta(days=100))
        output = StringIO()
        call_command('prune_reports', stdout=output)
        self.assertIn('No data deleted', output.getvalue())
        self.assertEqual(Report.objects.count(), 2)
        call_command('prune_reports', execute=True, stdout=StringIO())
        self.assertFalse(Report.objects.filter(pk=expired.pk).exists())
        self.assertTrue(Report.objects.filter(pk=archived.pk).exists())

    def test_old_reports_can_move_to_device_and_key_is_permanently_revoked(self):
        report = make_report()
        data = {'report_link': str(report.pk), 'token': 'test-owner-key'}
        response = self.client.post(reverse('core:import_legacy'), data)
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertIsNotNone(report.owner_id)
        self.assertFalse(check_password('test-owner-key', report.management_hash))
        other = Client()
        self.assertNotContains(other.get(reverse('core:manage', args=[report.pk])), 'Private messages')
        self.assertEqual(other.post(reverse('core:manage', args=[report.pk]), {'action': 'unlock', 'token': 'test-owner-key'}).status_code, 200)
        self.assertNotContains(other.get(reverse('core:manage', args=[report.pk])), 'Private messages')
        self.assertContains(self.client.get(reverse('core:my_reports')), report.title)

    def test_server_error_page_does_not_query_device_or_session_storage(self):
        from django.test import RequestFactory
        from .views import server_error
        request = RequestFactory().get('/')
        with self.assertNumQueries(0):
            response = server_error(request)
        self.assertContains(response, 'small detour', status_code=500)


@override_settings(SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class BilingualInterfaceTests(TestCase):
    def test_arabic_home_has_two_clear_actions_and_building_selection(self):
        response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='ar-SA')
        self.assertContains(response, 'lang="ar" dir="rtl"')
        self.assertContains(response, 'البحث عن المفقودات')
        self.assertContains(response, 'إضافة بلاغ')
        self.assertContains(response, 'مبنى الطلاب')
        self.assertContains(response, 'مبنى الطالبات')
        self.assertContains(response, 'English')
        self.assertNotContains(response, 'Copy key')

    def test_language_switch_keeps_device_and_preserves_browse_filters(self):
        first = self.client.get('/', HTTP_ACCEPT_LANGUAGE='ar')
        number = first.context['device_number']
        target = reverse('core:browse') + '?kind=found&building=women'
        response = self.client.post(reverse('set_language'), {'language': 'en', 'next': target})
        self.assertEqual(response.url, target)
        page = self.client.get(target)
        self.assertContains(page, 'lang="en" dir="ltr"')
        self.assertContains(page, 'Browse reports')
        self.assertEqual(page.context['device_number'], number)
        self.client.post(reverse('set_language'), {'language': 'ar', 'next': target})
        page = self.client.get(target)
        self.assertContains(page, 'lang="ar" dir="rtl"')
        self.assertContains(page, 'فئة الغرض')
        self.assertEqual(page.context['device_number'], number)

    def test_language_switch_rejects_missing_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/')
        response = client.post(reverse('set_language'), {'language': 'en'})
        self.assertEqual(response.status_code, 403)

    def test_arabic_form_labels_choices_and_validation_are_localized(self):
        url = reverse('core:submit', args=['lost'])
        response = self.client.get(url, HTTP_ACCEPT_LANGUAGE='ar')
        for label in ['اسم الغرض', 'المبنى', 'رقم القاعة / المعمل', 'صورة الغرض', 'بيانات التواصل', 'اختياري']:
            self.assertContains(response, label)
        nonce = response.context['submission_id']
        response = self.client.post(url, {**report_data(event_date=(timezone.localdate() + timedelta(days=1)).isoformat()), 'submission_id': nonce}, HTTP_ACCEPT_LANGUAGE='ar')
        self.assertContains(response, 'لا يمكن اختيار تاريخ في المستقبل.')
        self.assertContains(response, 'راجع التفاصيل التالية')
        self.assertEqual(Report.objects.count(), 0)

    def test_new_report_chooser_preserves_both_types(self):
        page = self.client.get(reverse('core:add_report'), HTTP_ACCEPT_LANGUAGE='ar')
        self.assertContains(page, reverse('core:submit', args=['lost']))
        self.assertContains(page, reverse('core:submit', args=['found']))
        self.assertContains(page, 'فقدت غرضًا')
        self.assertContains(page, 'عثرت على غرض')
        self.assertNotContains(page, 'password1')

    def test_color_and_classroom_filters_are_real_and_combined(self):
        matching = make_report(color='Blue', classroom='A-204', building='women')
        make_report(color='Red', classroom='A-204', building='women')
        make_report(color='Blue', classroom='A-205', building='women')
        page = self.client.get(reverse('core:browse'), {'color': 'blue', 'location': 'A-204', 'building': 'women'})
        self.assertEqual([r.pk for r in page.context['page_obj']], [matching.pk])

    @override_settings(DEBUG=False)
    def test_arabic_missing_report_and_throttle_feedback(self):
        page = self.client.get('/missing-page/', HTTP_ACCEPT_LANGUAGE='ar')
        self.assertContains(page, 'ضاعت الصفحة؟', status_code=404)
        self.assertNotContains(page, 'urlpatterns', status_code=404)
        with override_settings(REFOUND_RATE_LIMIT=0):
            page = self.client.post(reverse('core:submit', args=['lost']), {}, HTTP_ACCEPT_LANGUAGE='ar')
            self.assertContains(page, 'محاولات كثيرة', status_code=429)
