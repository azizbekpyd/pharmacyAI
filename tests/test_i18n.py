from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.accounts.templatetags.pharmacy_i18n import build_language_switch_path


class LanguageSwitchingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_language_switch_persists_for_follow_up_requests(self):
        response = self.client.post(
            reverse("set_language"),
            data={
                "language": "en",
                "next": "/login/",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lang="en"', html=False)

        localized_path = response.request["PATH_INFO"]
        follow_up = self.client.get(localized_path)

        self.assertEqual(follow_up.status_code, 200)
        self.assertContains(follow_up, 'lang="en"', html=False)

    def test_language_switch_path_strips_locale_prefix(self):
        request = self.factory.get("/ru/dashboard/?tab=main")
        self.assertEqual(build_language_switch_path(request), "/dashboard/?tab=main")

        request = self.factory.get("/en/dashboard/")
        self.assertEqual(build_language_switch_path(request), "/dashboard/")

        request = self.factory.get("/dashboard/?tab=main")
        self.assertEqual(build_language_switch_path(request), "/dashboard/?tab=main")

    @override_settings(ALLOWED_HOSTS=["testserver", "127.0.0.1", "localhost"])
    def test_language_switch_redirects_localized_dashboard_to_english(self):
        response = self.client.post(
            reverse("set_language"),
            data={
                "language": "en",
                "next": build_language_switch_path("/ru/dashboard/"),
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/en/dashboard/")
