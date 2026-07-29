"""Harga CLI custom exceptions and error handling."""


class HargaError(Exception):
    """Base exception for harga-cli."""

    exit_code = 1


class DatabaseError(HargaError):
    """Database connection or query error."""

    exit_code = 1


class ArgumentError(HargaError):
    """Invalid user arguments."""

    exit_code = 2


class NotFoundError(HargaError):
    """Requested resource not found."""

    exit_code = 1
