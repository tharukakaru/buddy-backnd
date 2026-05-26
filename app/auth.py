from fastapi import Header, HTTPException, status


def require_admin(x_user_role: str | None = Header(default=None)) -> None:
    """
    Demo-level admin guard for role-based admin endpoints.

    Frontend must send this header when calling /admin routes:

    X-User-Role: admin

    This is enough for project/demo integration, but it is not production auth.
    Real production auth should use JWT/session-based user identity.
    """
    if x_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    