"""CLI bootstrap tool — creates the first org-scoped admin user.

Usage (inside the Docker container):
    python -m app.cli.create_admin

Prompts interactively for email, full name, organization name, and password
(password input is hidden). Refuses to run if an org-scoped user already exists.
"""
from __future__ import annotations

import asyncio
import getpass
import sys

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.organization import Organization, OrgVertical
from app.models.user import User, UserRole


async def create_org_admin(
    session: AsyncSession,
    *,
    email: str,
    full_name: str,
    org_name: str,
    password: str,
    vertical: OrgVertical = OrgVertical.generic,
) -> User:
    """Create the first organization-scoped admin user.

    Finds the organization by name (reuses it if it already exists, which is the
    state after POST /api/v1/setup) or creates a new one. The session is NOT
    committed here — the caller is responsible for committing.

    Args:
        session: An open AsyncSession.
        email: The new user's email address.
        full_name: The new user's display name.
        org_name: Name of the organization to create or reuse.
        password: Plain-text password — will be hashed with bcrypt.

    Returns:
        The newly created User (flushed but not committed).

    Raises:
        ValueError: if password is too short or an org-scoped admin already exists.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    # Protection: refuse if any org-scoped user already exists.
    count = (
        await session.execute(
            select(func.count())
            .select_from(User)
            .where(User.organization_id.is_not(None))
        )
    ).scalar_one()
    if count > 0:
        raise ValueError(
            "An org admin already exists. Use the CRM UI to manage users."
        )

    # Reuse existing org (e.g. created by POST /api/v1/setup) or create a new one.
    org = (
        await session.execute(
            select(Organization).where(Organization.name == org_name)
        )
    ).scalar_one_or_none()

    if org is None:
        org = Organization(name=org_name, vertical=vertical)
        session.add(org)
        await session.flush()

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        is_global_admin=False,
        organization_id=org.id,
        role=UserRole.admin,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _main() -> None:
    print("=== Vortem CRM — Create Org Admin ===\n")
    email = input("Email: ").strip()
    full_name = input("Full name: ").strip()
    org_name = input("Organization name: ").strip()
    vertical_input = input("Vertical [generic/veterinary, default: generic]: ").strip() or "generic"
    password = getpass.getpass("Password (min 8 chars): ")

    try:
        vertical = OrgVertical(vertical_input)
    except ValueError:
        print(f"\nError: Unknown vertical '{vertical_input}'. Valid values: generic, veterinary.", file=sys.stderr)
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        try:
            user = await create_org_admin(
                session,
                email=email,
                full_name=full_name,
                org_name=org_name,
                password=password,
                vertical=vertical,
            )
            await session.commit()
            print("\nAdmin created successfully.")
            print(f"  Email   : {user.email}")
            print(f"  Name    : {user.full_name}")
            print(f"  Org ID  : {user.organization_id}")
            print(f"  Vertical: {vertical.value}")
            print("\nYou can now log in at http://localhost:3000")
        except ValueError as exc:
            print(f"\nError: {exc}", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            await session.rollback()
            print(f"\nUnexpected error: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(_main())
