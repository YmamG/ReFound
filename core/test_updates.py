from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from .forms import ReportForm
from .services.matching import score_pair
from .services.ai_matching import preview_matches, model
from .tests import make_report, report_data

@override_settings(LANGUAGE_CODE='en', REFOUND_AI_PREVIEW_ENABLED=False)
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

    def test_ai_disabled_does_not_load_model(self):
        report = make_report()
        with patch('core.services.ai_matching.model', side_effect=AssertionError('Must not load')):
            self.assertEqual(preview_matches(report)['mode'], 'rules')

    @override_settings(REFOUND_AI_PREVIEW_ENABLED=True)
    def test_ai_load_failure_uses_rules(self):
        report = make_report()
        candidate = make_report(kind='found')
        with patch('core.services.ai_matching.model', side_effect=RuntimeError('Unavailable')), self.assertLogs('core.services.ai_matching', level='WARNING'):
            result = preview_matches(report)
        self.assertEqual(result['mode'], 'rules')
        self.assertEqual(result['matches'][0].report.pk, candidate.pk)

    def test_public_preview_needs_no_login_and_hides_private_data(self):
        report = make_report()
        url = reverse('core:ai_preview', args=[report.pk])
        response = self.client.get(url)
        self.assertContains(response, 'rule-based fallback')
        self.assertNotContains(response, 'private@example.com')
        self.assertNotContains(response, '/admin/')
        report.is_hidden=True;report.save()
        self.assertEqual(self.client.get(url).status_code,404)

    @override_settings(REFOUND_RATE_LIMIT=1)
    def test_public_preview_is_rate_limited(self):
        report=make_report()
        url=reverse('core:ai_preview',args=[report.pk])
        self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(self.client.get(url).status_code,429)
        self.assertEqual(self.client.post(url).status_code,405)

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

    @override_settings(REFOUND_AI_PREVIEW_ENABLED=True)
    def test_ai_uses_public_text_only_and_respects_eligibility(self):
        report=make_report()
        eligible=make_report(kind='found')
        make_report(kind='found',is_hidden=True)
        make_report(kind='found',building='women')
        make_report(kind='found',status='resolved')
        class Query:
            def __matmul__(self,other): return other
        class Encoder:
            def encode(self,texts,**kwargs):
                self.texts=texts
                return [Query(),.8]
        encoder=Encoder()
        with patch('core.services.ai_matching.model',return_value=encoder):
            result=preview_matches(report)
        self.assertEqual(result['mode'],'ai')
        self.assertEqual([m.report.pk for m in result['matches']],[eligible.pk])
        self.assertEqual(len(encoder.texts),2)
        self.assertNotIn('private@example.com',str(encoder.texts))
        report.refresh_from_db();self.assertEqual(report.status,'active')

    @override_settings(REFOUND_AI_PREVIEW_ENABLED=True)
    def test_anonymous_visitor_can_receive_ai_results(self):
        report=make_report()
        candidate=make_report(kind='found')
        class Query:
            def __matmul__(self,other): return other
        class Encoder:
            def encode(self,*args,**kwargs): return [Query(),.8]
        with patch('core.services.ai_matching.model',return_value=Encoder()):
            response=self.client.get(reverse('core:ai_preview',args=[report.pk]))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['mode'],'ai')
        self.assertContains(response,candidate.title)
        self.assertNotContains(response,'private@example.com')

    @override_settings(REFOUND_AI_PREVIEW_ENABLED=True)
    def test_busy_model_returns_rules_without_loading_again(self):
        report=make_report();make_report(kind='found')
        with patch('core.services.ai_matching._MODEL_LOCK') as lock, patch('core.services.ai_matching.model') as encoder:
            lock.acquire.return_value=False
            self.assertEqual(preview_matches(report)['mode'],'rules')
            encoder.assert_not_called()
