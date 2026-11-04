from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


class PublicPageTests(SimpleTestCase):
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
