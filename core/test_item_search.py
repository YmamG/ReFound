"""Regression checks for the isolated, non-AI search experience."""
from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from .forms import MatchGameForm
from .models import Report
from .services.item_search import rank_items, item_tokens, room_key, primary_object
from .tests import make_report


@override_settings(LANGUAGE_CODE='en')
class ItemSearchTests(TestCase):
    def search(self, **changes):
        criteria = {'item': 'laptop bag', 'color': 'blue', 'search_kind': 'found'}
        criteria.update(changes)
        return rank_items(criteria)

    def found(self, **changes):
        return make_report(kind='found', **changes)

    def test_color_orders_same_objects_and_never_retrieves_color_alone(self):
        right = self.found()
        other = self.found(color='red')
        self.found(title='Blue keys', description='Blue keys.', category='keys')
        results = self.search()
        self.assertEqual([m.report.pk for m in results], [right.pk, other.pk])
        self.assertEqual(results[0].score, 100)
        self.assertTrue(results[1].color_conflict)

    def test_arabic_and_english_glossary_and_diacritics(self):
        report = self.found(title='حَقيبة لابتوب زرقاء', description='حقيبة من القماش', color='أزرق')
        self.assertEqual(self.search()[0].report.pk, report.pk)
        self.assertEqual(self.search(item='شنطة لابتوب', color='ازرق')[0].score, 100)
        self.assertEqual(item_tokens('حقيبة ظهر'), {'backpack', 'bag'})

    def test_room_normalization_keeps_letters_and_single_digits(self):
        self.assertEqual(room_key('A-٢٠٤'), room_key('a 204'))
        self.assertNotEqual(room_key('A-204'), room_key('B-204'))
        self.assertNotEqual(room_key('1'), room_key(''))
        a = self.found(classroom='A-204')
        self.found(classroom='B-204')
        self.assertEqual(self.search(classroom='A٢٠٤')[0].report.pk, a.pk)

    def test_compound_accessory_does_not_return_laptop_or_charger(self):
        report = self.found()
        self.found(title='Laptop charger', description='Blue laptop charger')
        self.found(title='Laptop', description='Laptop in blue')
        self.assertEqual([m.report.pk for m in self.search()], [report.pk])
        self.assertEqual(primary_object('phone with case'), 'phone')
        self.assertEqual(primary_object('phone case'), 'case')

    def test_only_eligible_reports_and_requested_building(self):
        report = self.found()
        self.found(is_hidden=True)
        self.found(status='resolved')
        make_report()
        self.found(building='women')
        archived = self.found()
        Report.objects.filter(pk=archived.pk).update(created_at=timezone.now()-timedelta(days=61))
        self.assertEqual([m.report.pk for m in self.search(building='students')], [report.pk])

    def test_optional_details_refine_order(self):
        self.found(location='Entrance', classroom='B204', category='other')
        right = self.found(location='Computing library', classroom='A204', category='bags')
        result = self.search(location='library', classroom='A204', category='bags')
        self.assertEqual(result[0].report.pk, right.pk)
        self.assertGreater(result[0].score, result[1].score)

    def test_missing_and_unknown_colors(self):
        self.found(color='')
        exact = self.found(color='turquoise')
        result = self.search(color='turquoise')
        self.assertEqual(result[0].report.pk, exact.pk)
        self.assertEqual(result[0].score, 100)
        self.assertLess(result[1].score, 100)

    def test_results_have_stable_order_and_limit(self):
        for _ in range(4):
            self.found()
        self.assertEqual([m.report.pk for m in self.search()], [m.report.pk for m in self.search()])
        self.assertEqual(len(rank_items({'item':'bag','color':'blue'}, limit=2)), 2)

    def test_form_rejects_generic_item_missing_color_and_future_date(self):
        for data in ({'item':'lost item','color':'blue'}, {'item':'bag'}, {'item':'bag','color':'blue','event_date':(timezone.localdate()+timedelta(days=1)).isoformat()}):
            self.assertFalse(MatchGameForm(data).is_valid())
        self.assertTrue(MatchGameForm({'item':'شنطة','color':'اسود'}).is_valid())

    def test_page_is_progressive_and_does_not_create_report_or_expose_contact(self):
        self.found()
        count = Report.objects.count()
        initial = self.client.get('/find-match/')
        self.assertEqual(initial.status_code, 200)
        self.assertNotContains(initial, 'class="match-options" open')
        response = self.client.get('/find-match/', {'item':'bag', 'color':'blue'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Blue laptop bag')
        self.assertNotContains(response, 'private@example.com')
        self.assertEqual(Report.objects.count(), count)
        self.assertEqual(self.client.post('/find-match/').status_code, 405)

    def test_validation_and_xss_are_rendered_safely(self):
        response = self.client.get('/find-match/', {'item':'<script>alert(1)</script>', 'color':'blue'})
        self.assertNotContains(response, '<script>alert(1)</script>')
        response = self.client.get('/find-match/', {'item':'bag','color':'blue','event_date':'invalid'})
        self.assertContains(response, 'class="match-options" open')
        self.assertContains(response, 'Enter a valid date.')
