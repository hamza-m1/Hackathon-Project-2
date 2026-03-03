from datetime import date, time

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .admin import BookingAdmin
from .models import Booking


class BookingAdminTests(TestCase):
    def setUp(self):
        self.booking = Booking.objects.create(
            player_name="Alice Example",
            player_email="alice@example.com",
            date=date(2026, 3, 5),
            start_time=time(10, 0),
            court_number=2,
        )
        user_model = get_user_model()
        self.superuser = user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin-pass-123",
        )
        self.user = user_model.objects.create_user(
            username="member",
            email="member@example.com",
            password="member-pass-123",
        )

    def test_booking_registered_in_admin(self):
        self.assertIn(Booking, admin.site._registry)
        self.assertIsInstance(admin.site._registry[Booking], BookingAdmin)

    def test_booking_admin_configuration(self):
        model_admin = admin.site._registry[Booking]
        self.assertEqual(model_admin.list_display, ("user", "court", "date", "time_slot"))
        self.assertEqual(model_admin.list_filter, ("date", "court_number", "player_name"))
        self.assertEqual(model_admin.search_fields, ("player_email", "player_name"))
        self.assertEqual(model_admin.ordering, ("date", "start_time"))

    def test_admin_can_access_booking_list_and_detail(self):
        self.client.force_login(self.superuser)

        changelist_url = reverse("admin:core_booking_changelist")
        change_url = reverse("admin:core_booking_change", args=[self.booking.pk])

        changelist_response = self.client.get(changelist_url)
        change_response = self.client.get(change_url)

        self.assertEqual(changelist_response.status_code, 200)
        self.assertEqual(change_response.status_code, 200)

    def test_non_admin_cannot_access_admin(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
