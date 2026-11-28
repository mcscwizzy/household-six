"""Household-scoped profile, access, password, and device-session administration."""

from datetime import datetime, timezone
import uuid

from app import permissions
from app.mutations import DomainError, clean, statement
from app.security import hash_password

COLORS = {"#233C32", "#78937D", "#C69A5D", "#54768C", "#9B6B72", "#7B6C9B"}
AVATARS = {"person", "fox", "bear", "rabbit", "sun", "leaf", "star"}
ADMIN_TARGET_ROLES = {"adult", "child", "display"}


def _audit(connection, actor, action):
    statement(connection, """INSERT INTO audit_log(id,household_id,actor_id,action)
        VALUES(:id,:household,:actor,:action)""", id=str(uuid.uuid4()),
        household=actor["household_id"], actor=actor["id"], action=action)


def _member(connection, actor, target_id):
    if not isinstance(target_id, str) or not target_id or len(target_id) > 64:
        raise DomainError(404, "This household member was not found.")
    result = statement(connection, """SELECT id,role,display_name,color,avatar_key,disabled_at
        FROM users WHERE id=:id AND household_id=:household""", id=target_id,
                      household=actor["household_id"]).mappings().first()
    if not result:
        raise DomainError(404, "This household member was not found.")
    return result


def _may_manage_target(actor, target, permission):
    if actor["id"] == target["id"]:
        return False
    if not permissions.allowed(actor["role"], permission):
        return False
    if actor["role"] == "admin" and target["role"] not in ADMIN_TARGET_ROLES:
        return False
    return target["role"] != "owner"


def update_profile(database, actor, target_id, data):
    if not isinstance(data, dict):
        raise DomainError(422, "Check the profile fields and try again.")
    data = {key: value for key, value in data.items() if key != "csrf"}
    if not data or set(data) - {"displayName", "color", "avatar"}:
        raise DomainError(422, "Check the profile fields and try again.")
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        target = _member(connection, actor, target_id)
        self_edit = actor["id"] == target_id and permissions.allowed(actor["role"], "profile.self.edit")
        managed_edit = _may_manage_target(actor, target, "members.manage")
        if not self_edit and not managed_edit:
            raise DomainError(403, "You are not allowed to edit this household profile.")
        name = clean(data["displayName"], 70, required=True) if "displayName" in data else target["display_name"]
        color = data.get("color", target["color"])
        avatar = data.get("avatar", target["avatar_key"])
        if not isinstance(color, str) or color not in COLORS or not isinstance(avatar, str) or avatar not in AVATARS:
            raise DomainError(422, "Choose an available profile color and avatar.")
        statement(connection, """UPDATE users SET display_name=:name,color=:color,avatar_key=:avatar
            WHERE id=:id AND household_id=:household""", name=name, color=color, avatar=avatar,
                  id=target_id, household=actor["household_id"])
        _audit(connection, actor, "member.profile.update")
        connection.commit()
    return {"id": target_id, "displayName": name, "role": target["role"], "color": color, "avatar": avatar}


def set_disabled(database, actor, target_id, disabled):
    if type(disabled) is not bool:
        raise DomainError(422, "Choose whether the account is active.")
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        target = _member(connection, actor, target_id)
        if not _may_manage_target(actor, target, "members.access.manage"):
            raise DomainError(403, "You are not allowed to change this account.")
        disabled_at = datetime.now(timezone.utc).isoformat() if disabled else None
        statement(connection, """UPDATE users SET disabled_at=:disabled WHERE id=:id AND household_id=:household""",
                  disabled=disabled_at, id=target_id, household=actor["household_id"])
        if disabled:
            statement(connection, "DELETE FROM sessions WHERE user_id=:id", id=target_id)
        _audit(connection, actor, "member.disable" if disabled else "member.reactivate")
        connection.commit()
    return {"id": target_id, "active": not disabled}


def reset_password(database, actor, target_id, password):
    if not isinstance(password, str) or not 12 <= len(password) <= 200:
        raise DomainError(422, "Choose a password between 12 and 200 characters.")
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        target = _member(connection, actor, target_id)
        if not _may_manage_target(actor, target, "members.password.reset"):
            raise DomainError(403, "You are not allowed to reset this account password.")
        statement(connection, """UPDATE users SET password_hash=:password WHERE id=:id AND household_id=:household""",
                  password=hash_password(password), id=target_id, household=actor["household_id"])
        statement(connection, "DELETE FROM sessions WHERE user_id=:id", id=target_id)
        _audit(connection, actor, "member.password.reset")
        connection.commit()
    return {"id": target_id, "sessionsRevoked": True}


def list_sessions(database, actor, target_id=None, current_id=None):
    target_id = target_id or actor["id"]
    with database.connect() as connection:
        target = _member(connection, actor, target_id)
        if actor["id"] != target_id and not _may_manage_target(actor, target, "sessions.manage.household"):
            raise DomainError(403, "You are not allowed to view this account's sessions.")
        rows = statement(connection, """SELECT device_id,created_at,expires_at,device_name FROM sessions
            WHERE user_id=:member AND device_id IS NOT NULL AND expires_at>:now
            ORDER BY created_at DESC,device_id""",
                         member=target_id, now=datetime.now(timezone.utc).isoformat()).mappings()
        return [{"id": row["device_id"], "createdAt": row["created_at"], "expiresAt": row["expires_at"],
                 "deviceName": row["device_name"], "current": row["device_id"] == current_id} for row in rows]


def revoke_session(database, actor, session_id, current_id=None):
    try:
        if not isinstance(session_id, str) or str(uuid.UUID(session_id)) != session_id:
            raise ValueError
    except ValueError:
        raise DomainError(404, "This session was not found.")
    with database.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        target = statement(connection, """SELECT u.id,u.role,s.device_id FROM sessions s JOIN users u ON u.id=s.user_id
            WHERE s.device_id=:session AND u.household_id=:household""",
                            session=session_id, household=actor["household_id"]).mappings().first()
        if not target:
            raise DomainError(404, "This session was not found.")
        allowed = (target["id"] == actor["id"]
                   or _may_manage_target(actor, target, "sessions.manage.household"))
        if not allowed:
            raise DomainError(403, "You are not allowed to revoke this session.")
        statement(connection, "DELETE FROM sessions WHERE device_id=:session", session=session_id)
        _audit(connection, actor, "session.revoke")
        connection.commit()
    return {"revoked": True, "current": session_id == current_id}
