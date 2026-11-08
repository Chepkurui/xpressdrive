import secrets

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from apps.core.validators import phone_validator


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self._create_user(email, password, **extra_fields)


def generate_customer_code():
    return "XD" + "".join(secrets.choice("0123456789") for _ in range(6))


class User(AbstractUser):
    """Cargo owner, driver or staff account. Email is the login identifier.

    customer_code identifies the account on bookings, waybills and phone calls.
    Drivers (is_driver) sign in to the mobile app to receive trip allocations
    and share their position while a trip is under way.
    """

    username = None
    email = models.EmailField("email address", unique=True)
    phone = models.CharField(max_length=20, blank=True, validators=[phone_validator])
    customer_code = models.CharField(max_length=12, unique=True, editable=False)
    is_driver = models.BooleanField(default=False, help_text="Can sign in to the driver app and be allocated trips.")
    licence_number = models.CharField("Driving licence no.", max_length=40, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        if not self.customer_code:
            code = generate_customer_code()
            while User.objects.filter(customer_code=code).exists():
                code = generate_customer_code()
            self.customer_code = code
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.customer_code})"
