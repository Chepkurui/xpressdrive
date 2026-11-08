from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r"^\+?[0-9][0-9 \-]{6,18}$",
    message="Enter a valid phone number, e.g. +256 700 000000.",
)
