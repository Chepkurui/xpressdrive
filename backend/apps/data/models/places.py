"""Towns, ports and border posts XpressDrive serves across East Africa.

Bookings, trips and empty legs use these codes for origin/destination so that
cargo and returning trucks can be matched on the same lane. Milestones shown
to cargo owners use the place *name* only, never coordinates.
"""
from django.db import models

# code: (name, country, kind)
PLACES = {
    # Uganda
    "kampala": ("Kampala", "Uganda", "city"),
    "entebbe": ("Entebbe", "Uganda", "city"),
    "jinja": ("Jinja", "Uganda", "city"),
    "mbale": ("Mbale", "Uganda", "city"),
    "tororo": ("Tororo", "Uganda", "city"),
    "mbarara": ("Mbarara", "Uganda", "city"),
    "kasese": ("Kasese", "Uganda", "city"),
    "fort_portal": ("Fort Portal", "Uganda", "city"),
    "gulu": ("Gulu", "Uganda", "city"),
    "lira": ("Lira", "Uganda", "city"),
    "arua": ("Arua", "Uganda", "city"),
    "kabale": ("Kabale", "Uganda", "city"),
    # Border posts
    "malaba": ("Malaba border", "Uganda / Kenya", "border"),
    "busia": ("Busia border", "Uganda / Kenya", "border"),
    "mpondwe": ("Mpondwe border", "Uganda / DR Congo", "border"),
    "bunagana": ("Bunagana border", "Uganda / DR Congo", "border"),
    "mahagi": ("Goli / Mahagi border", "Uganda / DR Congo", "border"),
    "katuna": ("Katuna / Gatuna border", "Uganda / Rwanda", "border"),
    "elegu": ("Elegu / Nimule border", "Uganda / South Sudan", "border"),
    "mutukula": ("Mutukula border", "Uganda / Tanzania", "border"),
    # Kenya
    "nairobi": ("Nairobi", "Kenya", "city"),
    "mombasa": ("Mombasa", "Kenya", "port"),
    "naivasha": ("Naivasha ICD", "Kenya", "port"),
    "nakuru": ("Nakuru", "Kenya", "city"),
    "eldoret": ("Eldoret", "Kenya", "city"),
    "kisumu": ("Kisumu", "Kenya", "city"),
    # Tanzania
    "dar_es_salaam": ("Dar es Salaam", "Tanzania", "port"),
    "mwanza": ("Mwanza", "Tanzania", "city"),
    "arusha": ("Arusha", "Tanzania", "city"),
    # Rwanda / Burundi
    "kigali": ("Kigali", "Rwanda", "city"),
    "bujumbura": ("Bujumbura", "Burundi", "city"),
    # DR Congo
    "goma": ("Goma", "DR Congo", "city"),
    "bukavu": ("Bukavu", "DR Congo", "city"),
    "beni": ("Beni", "DR Congo", "city"),
    "butembo": ("Butembo", "DR Congo", "city"),
    "bunia": ("Bunia", "DR Congo", "city"),
    "kisangani": ("Kisangani", "DR Congo", "city"),
    "aru": ("Aru", "DR Congo", "city"),
    # South Sudan
    "juba": ("Juba", "South Sudan", "city"),
}

PLACE_CHOICES = [(code, name) for code, (name, _country, _kind) in PLACES.items()]


def place_name(code):
    return PLACES.get(code, (code or "", "", ""))[0]


def place_field(verbose_name, **kw):
    return models.CharField(verbose_name, max_length=30, choices=PLACE_CHOICES, **kw)


def places_payload():
    return [
        {"code": code, "name": name, "country": country, "kind": kind}
        for code, (name, country, kind) in PLACES.items()
    ]
