from datetime import timedelta

from django.test import TestCase

from apps.accounts.models import User
from apps.tenants.models import Pharmacy


class TrialOnboardingTests(TestCase):
    def test_landing_page_for_anonymous_user(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start Free Trial")

    def test_root_redirects_authenticated_user_to_dashboard(self):
        user = User.objects.create_user(username="root_user", password="pass12345", role=User.ROLE_ADMIN)
        pharmacy = Pharmacy.objects.create(name="Root Pharmacy", owner=user)
        user.pharmacy = pharmacy
        user.save(update_fields=["pharmacy"])

        self.client.force_login(user)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard/")

    def test_start_trial_creates_admin_and_basic_plan(self):
        response = self.client.post(
            "/start-trial/",
            data={
                "pharmacy_name": "Trial Pharmacy",
                "username": "trial_admin",
                "email": "trial_admin@example.com",
                "password": "strongpass123",
                "password_confirm": "strongpass123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard/")

        user = User.objects.get(username="trial_admin")
        pharmacy = Pharmacy.objects.get(name="Trial Pharmacy")
        self.assertEqual(user.pharmacy_id, pharmacy.id)
        self.assertEqual(pharmacy.owner_id, user.id)
        self.assertEqual(pharmacy.plan_type, Pharmacy.PlanType.BASIC)
        self.assertTrue(pharmacy.is_active)
        self.assertEqual(pharmacy.max_users, 3)
        self.assertEqual(pharmacy.max_medicines, 200)
        self.assertEqual(pharmacy.max_monthly_sales, 1000)
        self.assertEqual((pharmacy.subscription_end - pharmacy.subscription_start), timedelta(days=14))
