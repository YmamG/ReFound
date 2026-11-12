from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from .forms import ReportForm
from .services.matching import score_pair
from .tests import make_report, report_data

@override_settings(LANGUAGE_CODE='en')
class UpdateTests(TestCase):
    def test_description_optional_but_short_supplied_text_rejected(self):
        form = ReportForm(report_data(description=''))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(ReportForm(report_data(description='short')).is_valid())

    def test_bilingual_color_and_item_rules(self):
        a = make_report(title='حقيبة لابتوب', color='أسود', description='')
        b = make_report(kind='found', title='Laptop bag', color='black', description='')
        score, reasons = score_pair(a, b)
        self.assertEqual(score, 100)
        self.assertIn('Same color', reasons)

    def test_browse_color_and_query_are_bilingual(self):
        report = make_report(color='black')
        for params in [{'color':'اسود'},{'color':'أسود'},{'q':'اسود'},{'q':'شنطة black'}]:
            response = self.client.get('/reports/', params)
            self.assertContains(response, str(report.pk))

    def test_optional_disclosure_opens_for_invalid_hidden_field(self):
        initial = self.client.get('/reports/new/lost/')
        nonce = initial.context['submission_id']
        response = self.client.post('/reports/new/lost/', {**report_data(description='short'), 'submission_id':nonce})
        self.assertContains(response, 'class="additional-info" open')

    def test_admin_can_edit_and_delete_but_visitors_cannot(self):
        report = make_report()
        url = reverse('admin:core_report_change', args=[report.pk])
        self.assertEqual(self.client.get(url).status_code,302)
        user=get_user_model().objects.create_superuser('moderator',password='test-only')
        self.client.force_login(user)
        data={**report_data(title='Edited by admin',description=''),'kind':'lost','status':'active'}
        self.assertEqual(self.client.post(url,data).status_code,302)
        report.refresh_from_db();self.assertEqual(report.title,'Edited by admin')
        self.assertEqual(self.client.post(reverse('admin:core_report_delete',args=[report.pk]),{'post':'yes'}).status_code,302)
        self.assertFalse(type(report).objects.filter(pk=report.pk).exists())
