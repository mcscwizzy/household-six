"""Explicit server-side permissions for the five household account roles."""

from types import MappingProxyType


_ALL_READ = {
    "calendar.read", "chores.read", "meals.read", "shopping.read", "rewards.read",
    "announcements.read", "habits.read", "display.read", "members.read", "profile.self.edit",
}
_ADULT_READ = _ALL_READ | {
    "inventory.read", "allowance.read", "budget.read", "maintenance.read", "vehicles.read",
    "devotional.private.read", "emergency.read", "documents.read", "sessions.manage.self",
    "password.change.self",
}
_ADULT_WRITE = {
    "calendar.write", "chores.manage", "meals.manage", "shopping.write", "rewards.manage",
    "reward.request", "inventory.manage", "announcements.manage", "habits.manage", "habit.check.self", "allowance.manage",
    "budget.manage", "maintenance.manage", "vehicles.manage", "devotional.manage",
    "emergency.manage", "documents.manage",
}

ROLE_PERMISSIONS = MappingProxyType({
    "owner": frozenset(_ADULT_READ | _ADULT_WRITE | {
        "members.manage", "members.access.manage", "members.password.reset", "sessions.manage.household",
        "parent_pin.manage", "invitations.manage", "display.configure", "assistant.use", "mcp.manage",
    }),
    "admin": frozenset(_ADULT_READ | _ADULT_WRITE | {
        "members.manage", "members.access.manage", "members.password.reset", "sessions.manage.household",
        "parent_pin.manage", "invitations.manage", "display.configure", "assistant.use", "mcp.manage",
    }),
    "adult": frozenset(_ADULT_READ | _ADULT_WRITE | {"assistant.use"}),
    "child": frozenset(_ALL_READ | {
        "shopping.write", "task.create.self", "chore.complete.assigned", "reward.request", "habit.check.self", "habit.manage.self", "allowance.read",
        "devotional.private.read", "devotional.note.self",
    }),
    "display": frozenset({
        "calendar.read", "chores.read", "meals.read", "announcements.read", "members.read", "display.read",
    }),
})


def allowed(role, permission):
    """Return False for unknown roles and operations so new actions fail closed."""
    return role in ROLE_PERMISSIONS and permission in ROLE_PERMISSIONS[role]
