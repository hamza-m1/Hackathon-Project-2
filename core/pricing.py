from datetime import time

from django.conf import settings


PEAK_START_TIME = time(17, 0)
PEAK_END_TIME = time(21, 0)


def parse_slot_time(slot_time):
    if isinstance(slot_time, time):
        return slot_time
    if isinstance(slot_time, str):
        return time.fromisoformat(slot_time)
    raise TypeError("slot_time must be a datetime.time or HH:MM string")


def is_peak_slot(slot_time):
    parsed_time = parse_slot_time(slot_time)
    return PEAK_START_TIME <= parsed_time < PEAK_END_TIME


def get_slot_price_pence(slot_time):
    if is_peak_slot(slot_time):
        return settings.STRIPE_BOOKING_PEAK_PRICE_PENCE
    return settings.STRIPE_BOOKING_OFF_PEAK_PRICE_PENCE


def format_price(pence_amount, currency):
    amount = pence_amount / 100
    if currency.lower() == "gbp":
        return f"£{amount:.2f}"
    return f"{currency.upper()} {amount:.2f}"


def get_slot_pricing(slot_time, currency):
    parsed_time = parse_slot_time(slot_time)
    price_pence = get_slot_price_pence(parsed_time)
    peak = is_peak_slot(parsed_time)
    return {
        "time": parsed_time,
        "is_peak": peak,
        "label": "Peak" if peak else "Off-peak",
        "price_pence": price_pence,
        "price_display": format_price(price_pence, currency),
    }
