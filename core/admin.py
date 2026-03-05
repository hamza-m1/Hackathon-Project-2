import logging

import stripe

from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from django_summernote.admin import SummernoteModelAdmin


from .models import Booking, ContactRequest, Court, SavedSlot, About


logger = logging.getLogger(__name__)


@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ("number", "surface", "is_available", "maintenance_start", "maintenance_end")
    list_filter = ("is_available", "surface", "indoors")
    list_editable = ("is_available",)
    search_fields = ("=number", "maintenance_reason")
    ordering = ("number",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "court",
        "date",
        "time_slot",
        "payment_status",
        "paid_at",
        "refunded_at",
        "stripe_refund_id",
    )
    list_filter = ("date", "court_number", "player_name", "payment_status")
    search_fields = ("player_email", "player_name", "stripe_refund_id")
    ordering = ("date", "start_time")
    actions = ["issue_stripe_refund"]

    @admin.display(ordering="player_name", description="User")
    def user(self, obj):
        return f"{obj.player_name} ({obj.player_email})"

    @admin.display(ordering="court_number", description="Court")
    def court(self, obj):
        return f"Court {obj.court_number}"

    @admin.display(ordering="start_time", description="Time Slot")
    def time_slot(self, obj):
        return obj.start_time

    @admin.action(description="Issue Stripe refund")
    def issue_stripe_refund(self, request, queryset):
        if not settings.STRIPE_SECRET_KEY:
            self.message_user(
                request,
                "Stripe secret key is missing. Refunds are disabled.",
                level=messages.ERROR,
            )
            logger.error(
                "Refund action aborted: STRIPE_SECRET_KEY is not set."
            )
            return

        stripe.api_key = settings.STRIPE_SECRET_KEY

        refunded_count = 0
        failed_count = 0
        for booking in queryset:
            if booking.payment_status == Booking.PaymentStatus.REFUNDED:
                self.message_user(
                    request,
                    (
                        f"Booking {booking.id}: refund skipped. "
                        "This booking is already marked as refunded."
                    ),
                    level=messages.WARNING,
                )
                continue

            if booking.payment_status not in {
                Booking.PaymentStatus.PAID,
                Booking.PaymentStatus.CANCELLED,
            }:
                self.message_user(
                    request,
                    (
                        f"Booking {booking.id}: refund skipped. "
                        "Only paid/cancelled bookings can be refunded."
                    ),
                    level=messages.WARNING,
                )
                continue

            if booking.stripe_refund_id:
                self.message_user(
                    request,
                    (
                        f"Booking {booking.id}: refund skipped. "
                        "This booking already has a Stripe refund id."
                    ),
                    level=messages.WARNING,
                )
                continue

            try:
                if booking.stripe_payment_intent_id:
                    refund = stripe.Refund.create(
                        payment_intent=booking.stripe_payment_intent_id,
                    )
                elif booking.stripe_charge_id:
                    refund = stripe.Refund.create(
                        charge=booking.stripe_charge_id,
                    )
                else:
                    failed_count += 1
                    self.message_user(
                        request,
                        (
                            f"Booking {booking.id}: refund skipped. "
                            "No Stripe payment id found on booking."
                        ),
                        level=messages.ERROR,
                    )
                    logger.error(
                        (
                            "Booking %s refund failed: "
                            "no payment_intent/charge id."
                        ),
                        booking.id,
                    )
                    continue

            except stripe.error.InvalidRequestError as exc:
                failed_count += 1
                error_message = getattr(exc, "user_message", str(exc))
                self.message_user(
                    request,
                    (
                        f"Booking {booking.id}: Stripe refund failed. "
                        f"{error_message}"
                    ),
                    level=messages.ERROR,
                )
                logger.exception(
                    "Booking %s refund invalid request.",
                    booking.id,
                )
                continue
            except stripe.error.StripeError as exc:
                failed_count += 1
                error_message = getattr(exc, "user_message", str(exc))
                self.message_user(
                    request,
                    (
                        f"Booking {booking.id}: Stripe refund failed. "
                        f"{error_message}"
                    ),
                    level=messages.ERROR,
                )
                logger.exception(
                    "Booking %s refund StripeError.",
                    booking.id,
                )
                continue

            booking.payment_status = Booking.PaymentStatus.REFUNDED
            booking.refunded_at = timezone.now()
            booking.stripe_refund_id = refund.get("id", "")
            booking.save(
                update_fields=[
                    "payment_status",
                    "refunded_at",
                    "stripe_refund_id",
                ]
            )
            refunded_count += 1

        if refunded_count:
            self.message_user(
                request,
                f"Issued Stripe refunds for {refunded_count} booking(s).",
                level=messages.SUCCESS,
            )

        if failed_count:
            self.message_user(
                request,
                f"Refund failed for {failed_count} booking(s).",
                level=messages.WARNING,
            )


@admin.register(SavedSlot)
class SavedSlotAdmin(admin.ModelAdmin):
    list_display = ("owner", "court_number", "date", "start_time", "surface")
    list_filter = ("date", "surface")
    search_fields = ("owner__username", "owner__email")
    ordering = ("date", "start_time", "court_number")


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ("owner", "booking", "subject", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = (
        "owner__username",
        "owner__email",
        "subject",
        "message",
    )
    ordering = ("-created_at",)


@admin.register(About)
class AboutAdmin(SummernoteModelAdmin):
    list_display = ("title", "last_updated")
    search_fields = ("title",)
    ordering = ("-last_updated",)
    summernote_fields = ("content",)
