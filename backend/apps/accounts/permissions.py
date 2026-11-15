from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import User

QUALITY_ROLES = (User.Role.QUALITY, User.Role.ADMIN)
ENGINEER_ROLES = (User.Role.ENGINEER, User.Role.QUALITY, User.Role.ADMIN)


def has_role(user, *roles) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.role in roles


def is_admin(user) -> bool:
    return has_role(user, User.Role.ADMIN)


def is_quality_or_admin(user) -> bool:
    return has_role(user, *QUALITY_ROLES)


def is_engineer_or_above(user) -> bool:
    return has_role(user, *ENGINEER_ROLES)


class IsAdminRole(BasePermission):
    message = "Требуется роль администратора"

    def has_permission(self, request, view):
        return is_admin(request.user)


class IsQualityOrAdmin(BasePermission):
    message = "Действие доступно менеджеру по качеству или администратору"

    def has_permission(self, request, view):
        return is_quality_or_admin(request.user)


class IsEngineerOrAbove(BasePermission):
    message = (
        "Действие доступно инженеру-конструктору, менеджеру по качеству "
        "или администратору"
    )

    def has_permission(self, request, view):
        return is_engineer_or_above(request.user)


class ReadOnly(BasePermission):
    message = "Доступ только для чтения"

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
