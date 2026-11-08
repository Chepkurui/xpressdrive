"""Demo data for XpressDrive: cargo owners, drivers, trucks, trips on real
East African lanes (with GPS trails along the road), empty legs and bookings.

    python manage.py seed_demo

Everything uses @sample.xpressdrive.test accounts and is tagged, so re-running
replaces only the previous demo data. All demo accounts use SAMPLE_PASSWORD.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.data.models import (
    Category,
    DeliveryOption,
    DriverResponse,
    EmptyLeg,
    EmptyLegStatus,
    PaymentStatus,
    ServiceType,
    Shipment,
    ShipmentStatus as S,
    ShippingMode as M,
    SpaceType,
    TrackingEvent,
    Trip,
    TripEvent,
    TripPosition,
    TripStatus as T,
    Truck,
    TruckType,
    place_name,
)

DOMAIN = "sample.xpressdrive.test"
SAMPLE_PASSWORD = "Admin@123"
TAG = "[demo]"

# Road corridors as (place code or label, lat, lng). Coordinates are approximate.
NORTHERN_CORRIDOR = [
    ("mombasa", -4.043, 39.668), ("Mariakani", -3.862, 39.474), ("Voi", -3.396, 38.556), ("Mtito Andei", -2.690, 38.166),
    ("Emali", -2.080, 37.470), ("Athi River", -1.456, 36.978), ("nairobi", -1.286, 36.817), ("naivasha", -0.717, 36.431),
    ("nakuru", -0.303, 36.080), ("eldoret", 0.514, 35.270), ("Bungoma", 0.563, 34.561), ("malaba", 0.636, 34.281),
    ("tororo", 0.693, 34.181), ("Iganga", 0.609, 33.469), ("jinja", 0.447, 33.204), ("Mukono", 0.353, 32.755), ("kampala", 0.347, 32.582),
]
KAMPALA_GOMA = [
    ("kampala", 0.347, 32.582), ("Mpigi", 0.229, 32.314), ("Masaka", -0.333, 31.734), ("Lyantonde", -0.405, 31.157),
    ("mbarara", -0.607, 30.655), ("Ntungamo", -0.879, 30.264), ("kabale", -1.249, 29.989), ("Kisoro", -1.285, 29.685),
    ("bunagana", -1.287, 29.597), ("Rutshuru", -1.186, 29.447), ("goma", -1.679, 29.222),
]
KAMPALA_JUBA = [
    ("kampala", 0.347, 32.582), ("Luwero", 0.849, 32.473), ("Kafu", 1.415, 32.006), ("Karuma", 2.249, 32.245),
    ("gulu", 2.775, 32.299), ("Atiak", 3.271, 32.118), ("elegu", 3.581, 32.064), ("Nimule", 3.596, 32.064), ("juba", 4.851, 31.582),
]
KAMPALA_KIGALI = KAMPALA_GOMA[:7] + [("katuna", -1.360, 29.985), ("Byumba", -1.578, 30.067), ("kigali", -1.950, 30.059)]

DRIVERS = [
    ("Ssali", "Ronald", "DL-UG-0042119"), ("Wanyama", "Peter", "DL-KE-7718203"), ("Mugabe", "Joseph", "DL-UG-0098812"),
    ("Lokwang", "Simon", "DL-UG-0110947"), ("Otieno", "Kevin", "DL-KE-6620019"), ("Habimana", "Eric", "DL-RW-1183301"),
]
TRUCKS = [
    ("UBK 412X", "ZE 2214", TruckType.CONTAINER_40, "Scania R460", 30000, 67, "kampala"),
    ("KDA 218L", "ZF 8812", TruckType.FLATBED, "Mercedes Actros 2645", 28000, None, "mombasa"),
    ("UBJ 905Q", "ZD 4410", TruckType.CONTAINER_20, "Howo Sinotruk", 24000, 33, "kampala"),
    ("UBM 330A", "", TruckType.RIGID, "Isuzu FVZ", 12000, 45, "kampala"),
    ("KCZ 771P", "ZC 1907", TruckType.CONTAINER_40, "Volvo FH 440", 30000, 67, "mombasa"),
    ("RAD 642B", "", TruckType.BOX_TRAILER, "MAN TGS 33.400", 26000, 80, "kigali"),
]
CUSTOMERS = [
    ("Nakato", "Sarah", "Nakato Supermarkets Ltd"), ("Okello", "David", "Okello Hardware"), ("Namubiru", "Grace", "Grace Fashions"),
    ("Mugisha", "Brian", "Mugisha Agro Traders"), ("Achieng", "Joan", "Joan Beverages Distributors"),
    ("Kabila", "Patrick", "Goma Import Centre"), ("Deng", "Mary", "Juba General Supplies"), ("Kato", "Moses", "Kato Motor Spares"),
]
GOODS = [
    ("Bagged cement (50 kg x 400)", Category.BUILDING, M.FULL_TRUCK, 400, 20000, None),
    ("Cooking oil, 20 L jerrycans", Category.FMCG, M.PART_LOAD, 120, 2500, Decimal("4.200")),
    ("Motorcycle spare parts (cartons)", Category.MACHINERY, M.PARCEL, 14, 380, None),
    ("Second-hand clothes bales", Category.CLOTHING, M.PART_LOAD, 60, 3000, Decimal("9.000")),
    ("Maize flour, 25 kg bags", Category.AGRICULTURE, M.PART_LOAD, 200, 5000, Decimal("8.500")),
    ("Soft drinks (crates)", Category.FMCG, M.PART_LOAD, 300, 6000, Decimal("12.000")),
    ("Iron sheets & roofing nails", Category.BUILDING, M.PART_LOAD, 150, 4200, Decimal("6.000")),
    ("Solar panels and batteries", Category.ELECTRONICS, M.PARCEL, 20, 520, None),
    ("Household furniture", Category.HOME, M.PART_LOAD, 12, 900, Decimal("10.500")),
    ("Imported tiles (container)", Category.BUILDING, M.CONTAINER_40, 1, 26000, None),
    ("Electronics (container)", Category.ELECTRONICS, M.CONTAINER_20, 1, 12000, None),
]


def interpolate(route, fraction, points):
    """`points` positions evenly spaced along the first `fraction` of the route."""
    legs = list(zip(route, route[1:]))
    out = []
    for i in range(points):
        f = fraction * i / max(points - 1, 1) * len(legs)
        k = min(int(f), len(legs) - 1)
        t = f - k
        (_, a_lat, a_lng), (_, b_lat, b_lng) = legs[k]
        out.append((a_lat + (b_lat - a_lat) * t, a_lng + (b_lng - a_lng) * t))
    return out


def passed(route, fraction):
    """Named points the truck has passed at `fraction` of the route."""
    n = int(fraction * (len(route) - 1))
    return route[1:n + 1]


class Command(BaseCommand):
    help = "Create demo customers, drivers, trucks, trips with GPS trails, empty legs and bookings (re-runnable)."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=11)

    @transaction.atomic
    def handle(self, seed, **opts):
        rnd = random.Random(seed)
        User = get_user_model()
        now, today = timezone.now(), timezone.localdate()

        # ------------------------------------------------------------ reset
        old = User.objects.filter(email__endswith=f"@{DOMAIN}")
        Shipment.objects.filter(owner__in=old, parent__isnull=False).delete()
        Shipment.objects.filter(owner__in=old).delete()
        Trip.objects.filter(notes__startswith=TAG).delete()
        Truck.objects.filter(notes__startswith=TAG).delete()
        old.delete()

        # ------------------------------------------------------------ people & trucks
        def person(first, last, **kw):
            u = User.objects.create_user(f"{first.lower()}.{last.lower()}@{DOMAIN}", SAMPLE_PASSWORD, first_name=first,
                                         last_name=last, phone=f"+2567{rnd.choice('0578')}{rnd.randint(1000000, 9999999)}", **kw)
            return u

        drivers = [person(f, l, is_driver=True, licence_number=lic) for l, f, lic in DRIVERS]
        customers = [person(f, l) for l, f, _co in CUSTOMERS]
        trucks = []
        for (plate, trailer, kind, model, kg, cbm, base), driver in zip(TRUCKS, drivers):
            trucks.append(Truck.objects.create(
                plate_number=plate, trailer_plate=trailer, truck_type=kind, make_model=model, capacity_kg=Decimal(kg),
                capacity_cbm=Decimal(cbm) if cbm else None, home_base=base, default_driver=driver,
                owner_name=rnd.choice(["XpressDrive fleet", "Mutebi Transporters", "Coast Haulage Ltd"]),
                notes=f"{TAG} demo truck",
            ))

        # ------------------------------------------------------------ helpers
        def trip(route, status, driver_i, *, backhaul=False, dep_days=0, eta_days=2, fraction=0.0, stale=False, response=None):
            o, d = route[0][0], route[-1][0]
            truck = trucks[driver_i] if driver_i is not None else None
            t = Trip.objects.create(
                origin=o, destination=d, status=status, is_backhaul=backhaul, truck=truck,
                driver=drivers[driver_i] if driver_i is not None and status != T.PLANNED else None,
                capacity_kg=truck.capacity_kg if truck else Decimal("28000"), capacity_cbm=truck.capacity_cbm if truck else None,
                carrier_reference=f"MSKU {rnd.randint(1000000, 9999999)}" if truck and "container" in truck.truck_type else "",
                departure_date=today - timedelta(days=dep_days), eta_date=today + timedelta(days=eta_days),
                notes=f"{TAG} demo trip", driver_response=response or (DriverResponse.ACCEPTED if driver_i is not None and status != T.PLANNED else ""),
                allocated_at=now - timedelta(days=dep_days + 1) if driver_i is not None else None,
                responded_at=now - timedelta(days=dep_days + 1, hours=-1) if response != DriverResponse.PENDING and driver_i is not None else None,
                started_at=now - timedelta(days=dep_days) if status in (T.IN_TRANSIT, T.AT_BORDER, T.ARRIVED, T.COMPLETED) else None,
                completed_at=now - timedelta(days=1) if status == T.COMPLETED else None,
            )
            TripEvent.objects.create(trip=t, kind="note", status=T.PLANNED, note="Trip created.")
            if t.driver_id:
                TripEvent.objects.create(trip=t, kind="allocation", status=T.ALLOCATED, note=f"Allocated to {t.driver.get_full_name()}.")
            if fraction and t.driver_id:
                hours = max(dep_days * 24, 6)
                pts = interpolate(route, fraction, 120)
                end = now - (timedelta(hours=2, minutes=20) if stale else timedelta(minutes=rnd.randint(1, 4)))
                start = end - timedelta(hours=hours)
                step = (end - start) / len(pts)
                TripPosition.objects.bulk_create([
                    TripPosition(trip=t, driver=t.driver, lat=Decimal(f"{la + rnd.uniform(-0.0004, 0.0004):.6f}"),
                                 lng=Decimal(f"{ln + rnd.uniform(-0.0004, 0.0004):.6f}"), speed_kmh=round(rnd.uniform(35, 72), 1),
                                 heading=None, accuracy_m=round(rnd.uniform(4, 15), 1), recorded_at=start + step * (i + 1))
                    for i, (la, ln) in enumerate(pts)
                ])
                la, ln = pts[-1]
                Trip.objects.filter(pk=t.pk).update(last_lat=Decimal(f"{la:.6f}"), last_lng=Decimal(f"{ln:.6f}"),
                                                    last_speed_kmh=0.0 if status == T.AT_BORDER else 58.0, last_position_at=end)
                for name, la, ln in passed(route, fraction):
                    TripEvent.objects.create(trip=t, kind="checkpoint", status=T.IN_TRANSIT, place=name if name.islower() else "",
                                             place_label=place_name(name) if name.islower() else name,
                                             lat=Decimal(f"{la:.6f}"), lng=Decimal(f"{ln:.6f}"), created_by=t.driver)
            t.refresh_from_db()
            return t

        def booking(owner, goods, route, status, *, trip=None, age=3, checkpoints=(), hold=None):
            desc, cat, mode, qty, kg, cbm = goods
            o, d = route[0][0], route[-1][0]
            measured = status not in (S.BOOKED, S.CANCELLED)
            pay = (PaymentStatus.PENDING if not measured else
                   PaymentStatus.PAID if status == S.DELIVERED else rnd.choice([PaymentStatus.PAID, PaymentStatus.UNPAID]))
            charge = {M.PARCEL: kg * Decimal("0.9"), M.PART_LOAD: (cbm or 1) * 38, M.FULL_TRUCK: 1500,
                      M.CONTAINER_20: 1900, M.CONTAINER_40: 2600}[mode]
            delivery = rnd.random() < 0.5
            s = Shipment.objects.create(
                owner=owner, trip=trip, origin=o, destination=d, mode=mode, category=cat, description=desc, quantity=qty,
                service_type=ServiceType.DEDICATED if mode in (M.FULL_TRUCK, M.CONTAINER_20, M.CONTAINER_40) else ServiceType.CONSOLIDATED,
                pickup_address=f"{rnd.choice(['Plot 12 Industrial Area', 'Kilindini Port, Berth 7', 'Gate 3, ICD', 'Nakawa Market'])}, {place_name(o)}",
                pickup_date=today - timedelta(days=max(age - 1, 0)), declared_weight_kg=Decimal(kg),
                declared_value_usd=Decimal(rnd.randint(800, 45000)), is_fragile=cat in (Category.ELECTRONICS, Category.HOME),
                consignee_name=rnd.choice(["Store manager", "Warehouse supervisor", "Mr. Bahati", "Mrs. Uwase", "Accounts office"]),
                consignee_phone=f"+2567{rnd.randint(10000000, 99999999)}",
                delivery_option=DeliveryOption.DELIVERY if delivery else DeliveryOption.PICKUP,
                delivery_address=f"Main street, {place_name(d)}" if delivery else "",
                weight_kg=Decimal(kg) if measured else None, volume_cbm=cbm if measured else None,
                packages_received=qty if measured else None,
                charge_usd=Decimal(charge).quantize(Decimal("0.01")) if measured else None, payment_status=pay,
                eta_date=trip.eta_date if trip else None, internal_notes=f"{TAG} demo booking",
            )
            s.events.all().delete()
            path = [S.BOOKED, S.CONFIRMED, S.ALLOCATED, S.LOADED, S.IN_TRANSIT, S.AT_BORDER, S.ARRIVED, S.DELIVERED]
            if status in (S.ON_HOLD, S.CANCELLED):
                steps = [S.BOOKED, S.CONFIRMED, status] if status == S.ON_HOLD else [S.BOOKED, status]
            else:
                steps = path[: path.index(status) + 1]
                if S.AT_BORDER in steps and status != S.AT_BORDER:
                    steps.remove(S.AT_BORDER)
            start = now - timedelta(days=age)
            stamp = lambda i, n: start + (now - start) * (i + 1) / (n + 2)  # noqa: E731
            rows = []
            for i, st in enumerate(steps):
                loc = s.default_location(st)
                note = {S.BOOKED: "Booking received.", S.CONFIRMED: "Quote accepted, booking confirmed.",
                        S.ALLOCATED: "A truck has been allocated to your cargo.", S.LOADED: "Cargo loaded and sealed.",
                        S.IN_TRANSIT: "On the road.", S.ARRIVED: "Arrived. We will call the receiver.",
                        S.DELIVERED: "Delivered and signed for.", S.CANCELLED: "Cancelled at customer's request.",
                        S.ON_HOLD: hold or ""}.get(st, "")
                if st == S.AT_BORDER:
                    loc, note = place_name(route[-3][0]) if route[-3][0].islower() else route[-3][0], "Clearing customs at the border."
                rows.append(TrackingEvent(shipment=s, status=st, location=loc, note=note, created_at=stamp(i, len(steps) + len(checkpoints))))
                if st == S.IN_TRANSIT:
                    for j, (name, _la, _ln) in enumerate(checkpoints):
                        rows.append(TrackingEvent(shipment=s, status=S.IN_TRANSIT, location=place_name(name) if name.islower() else name,
                                                  created_at=stamp(i, len(steps) + len(checkpoints)) + timedelta(hours=2 * (j + 1))))
            TrackingEvent.objects.bulk_create(rows)
            Shipment.objects.filter(pk=s.pk).update(
                status=status, created_at=start,
                received_at=start + timedelta(days=1) if status in path and path.index(status) >= path.index(S.LOADED) else None,
                delivered_at=now - timedelta(days=1) if status == S.DELIVERED else None,
            )
            return s

        reverse = lambda r: list(reversed(r))  # noqa: E731
        c = customers

        # 1. Mombasa → Kampala, 40ft, in transit past Eldoret
        t1 = trip(NORTHERN_CORRIDOR, T.IN_TRANSIT, 0, dep_days=2, eta_days=1, fraction=0.62)
        cps = passed(NORTHERN_CORRIDOR, 0.62)
        for owner, g in [(c[0], GOODS[1]), (c[2], GOODS[3]), (c[7], GOODS[2]), (c[4], GOODS[5])]:
            booking(owner, g, NORTHERN_CORRIDOR, S.IN_TRANSIT, trip=t1, age=4, checkpoints=[p for p in cps if p[0].islower()])

        # 2. Kampala → Goma, flatbed, held at Bunagana border
        t2 = trip(KAMPALA_GOMA, T.AT_BORDER, 1, dep_days=2, eta_days=1, fraction=0.8)
        for owner, g in [(c[5], GOODS[0]), (c[5], GOODS[6])]:
            booking(owner, g, KAMPALA_GOMA, S.AT_BORDER, trip=t2, age=5)

        # 3. Nairobi → Kampala: empty container returning to base, filled with backhaul cargo; phone not reporting
        nbo_kla = NORTHERN_CORRIDOR[6:]
        t3 = trip(nbo_kla, T.IN_TRANSIT, 2, backhaul=True, dep_days=1, eta_days=1, fraction=0.35, stale=True)
        for owner, g in [(c[1], GOODS[6]), (c[3], GOODS[4])]:
            booking(owner, g, nbo_kla, S.IN_TRANSIT, trip=t3, age=3)

        # 4. Kampala → Juba, accepted, loading in Kampala
        t4 = trip(KAMPALA_JUBA, T.LOADING, 3, dep_days=0, eta_days=3, fraction=0.001)
        for owner, g in [(c[6], GOODS[5]), (c[6], GOODS[8]), (c[0], GOODS[2])]:
            booking(owner, g, KAMPALA_JUBA, S.LOADED, trip=t4, age=2)

        # 5. Kampala → Mombasa backhaul from a driver's empty-leg offer, allocated and awaiting the driver
        kla_mba = reverse(NORTHERN_CORRIDOR)
        t5 = trip(kla_mba, T.ALLOCATED, 4, backhaul=True, dep_days=-2, eta_days=5, response=DriverResponse.PENDING)
        EmptyLeg.objects.create(driver=drivers[4], truck=trucks[4], origin="kampala", destination="mombasa",
                                available_from=today + timedelta(days=2), space=SpaceType.EMPTY_CONTAINER_40,
                                capacity_kg=Decimal("30000"), capacity_cbm=Decimal("67"), status=EmptyLegStatus.MATCHED, trip=t5,
                                notes="Returning the empty box to the port.")
        booking(c[3], GOODS[4], kla_mba, S.CONFIRMED, trip=t5, age=1)

        # 6. Mombasa → Kigali, planned, no driver yet
        mba_kgl = NORTHERN_CORRIDOR + KAMPALA_KIGALI[1:]
        t6 = trip(mba_kgl, T.PLANNED, None, dep_days=-3, eta_days=8)
        booking(c[4], GOODS[10], mba_kgl, S.CONFIRMED, trip=t6, age=2)

        # 7. Completed last week
        t7 = trip(NORTHERN_CORRIDOR, T.COMPLETED, 5, dep_days=9, eta_days=-5)
        for owner, g in [(c[0], GOODS[9]), (c[7], GOODS[2])]:
            booking(owner, g, NORTHERN_CORRIDOR, S.DELIVERED, trip=t7, age=12)

        # Open empty legs (drivers going back empty) and cargo still needing a truck
        EmptyLeg.objects.create(driver=drivers[5], truck=trucks[5], origin="goma", destination="kampala",
                                available_from=today + timedelta(days=1), available_until=today + timedelta(days=3),
                                space=SpaceType.EMPTY_TRUCK, capacity_kg=Decimal("26000"), notes="Box trailer, can load at Goma town.")
        EmptyLeg.objects.create(driver=drivers[1], truck=trucks[1], origin="kampala", destination="mombasa",
                                available_from=today + timedelta(days=3), space=SpaceType.EMPTY_TRUCK,
                                capacity_kg=Decimal("28000"), notes="Flatbed, back to the coast after Goma.")
        EmptyLeg.objects.create(driver=drivers[2], truck=trucks[2], origin="kampala", destination="nairobi",
                                available_from=today + timedelta(days=4), space=SpaceType.EMPTY_CONTAINER_20, capacity_cbm=Decimal("33"))
        booking(c[1], GOODS[0], [("kampala", 0, 0), ("mombasa", 0, 0)], S.CONFIRMED, age=1)
        booking(c[2], GOODS[3], [("kampala", 0, 0), ("goma", 0, 0)], S.BOOKED, age=0)
        booking(c[3], GOODS[4], [("mbarara", 0, 0), ("kigali", 0, 0)], S.BOOKED, age=0)
        booking(c[7], GOODS[7], [("nairobi", 0, 0), ("kampala", 0, 0)], S.ON_HOLD, age=4,
                hold="Waiting for the import declaration from the shipper.")

        self.stdout.write(self.style.SUCCESS(
            f"Demo data ready: {len(customers)} cargo owners, {len(drivers)} drivers, {len(trucks)} trucks, "
            f"{Trip.objects.filter(notes__startswith=TAG).count()} trips, "
            f"{Shipment.objects.filter(internal_notes__startswith=TAG).count()} bookings. "
            f"Sign in as e.g. ronald.ssali@{DOMAIN} (driver) or sarah.nakato@{DOMAIN} (cargo owner), password {SAMPLE_PASSWORD}."
        ))
