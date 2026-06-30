"""Tests de aislamiento multi-organización.

Cubre H-015 (IDOR en GET /stages), H-016 (assigned_to cross-org),
H-017 (FKs de Deal cross-org) y H-022 (conversión con stage cross-org).

Patrón: org_a (test_org + test_user) ya viene de conftest.
org_b y sus recursos se crean inline en cada test o en fixtures locales.

Los tests que verifican una vulnerabilidad ESTÁN ESCRITOS con la semántica
correcta (asserting the DESIRED security behavior). Antes del fix, algunos
fallaban porque el código no implementaba el rechazo. Tras el fix, todos pasan.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.organization import Organization
from app.models.pipeline import Pipeline
from app.models.stage import Stage
from app.models.user import User, UserRole

LEADS_URL = "/api/v1/leads"
CONTACTS_URL = "/api/v1/contacts"
DEALS_URL = "/api/v1/deals"
STAGES_URL = "/api/v1/stages"
SUPERVISOR_URL = "/api/v1/supervisor"
CONVERSION_URL = "/api/v1/leads/{lead_id}/convert"


# ─── Fixtures org B ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def org_b(session: AsyncSession) -> Organization:
    org = Organization(name="Org B — Isolation Tests")
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return org


@pytest_asyncio.fixture()
async def user_b(session: AsyncSession, org_b: Organization) -> User:
    user = User(
        email="admin_b_isolation@test.com",
        full_name="Admin Org B",
        hashed_password=hash_password("passB123456"),
        is_active=True,
        organization_id=org_b.id,
        is_global_admin=False,
        role=UserRole.admin,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def agent_b(session: AsyncSession, org_b: Organization) -> User:
    user = User(
        email="agent_b_isolation@test.com",
        full_name="Agent Org B",
        hashed_password=hash_password("passB123456"),
        is_active=True,
        organization_id=org_b.id,
        is_global_admin=False,
        role=UserRole.agent,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def pipeline_b(session: AsyncSession, org_b: Organization) -> Pipeline:
    p = Pipeline(organization_id=org_b.id, name="Pipeline Org B")
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@pytest_asyncio.fixture()
async def stage_b(session: AsyncSession, org_b: Organization, pipeline_b: Pipeline) -> Stage:
    s = Stage(
        organization_id=org_b.id,
        pipeline_id=pipeline_b.id,
        name="Stage Org B",
        order=1,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


@pytest_asyncio.fixture()
async def contact_b(session: AsyncSession, org_b: Organization) -> Contact:
    c = Contact(
        organization_id=org_b.id,
        first_name="Contact",
        last_name="OrgB",
    )
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return c


@pytest_asyncio.fixture()
async def lead_a(session: AsyncSession, test_org: Organization) -> Lead:
    """Lead belonging to org A (the default test org)."""
    lead = Lead(
        organization_id=test_org.id,
        first_name="Lead",
        last_name="OrgA",
        email="lead_a_isolation@test.com",
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return lead


# ─── Fixtures org A (resources needed by cross-org tests) ─────────────────────


@pytest_asyncio.fixture()
async def pipeline_a(session: AsyncSession, test_org: Organization) -> Pipeline:
    p = Pipeline(organization_id=test_org.id, name="Pipeline Org A")
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@pytest_asyncio.fixture()
async def stage_a(session: AsyncSession, test_org: Organization, pipeline_a: Pipeline) -> Stage:
    s = Stage(
        organization_id=test_org.id,
        pipeline_id=pipeline_a.id,
        name="Stage Org A",
        order=1,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


@pytest_asyncio.fixture()
async def contact_a(session: AsyncSession, test_org: Organization) -> Contact:
    c = Contact(
        organization_id=test_org.id,
        first_name="Contact",
        last_name="OrgA",
    )
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return c


@pytest_asyncio.fixture()
async def supervisor_a(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="supervisor_a_isolation@test.com",
        full_name="Supervisor Org A",
        hashed_password=hash_password("passA123456"),
        is_active=True,
        organization_id=test_org.id,
        is_global_admin=False,
        role=UserRole.supervisor,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ─── H-015: IDOR en GET /stages ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_stages_returns_empty_for_other_org_pipeline(
    client: AsyncClient,
    access_token: str,
    pipeline_b: Pipeline,
    stage_b: Stage,
    user_b: User,
) -> None:
    """H-015: Un usuario de org A que consulta GET /stages?pipeline_id=<pipeline_b>
    debe recibir una lista vacía, no los stages de org B.

    Demuestra la vulnerabilidad IDOR: el endpoint filtraba solo por pipeline_id
    sin validar que el pipeline pertenezca a la org del token.
    """
    # Usuario de org A intenta leer stages de un pipeline que pertenece a org B.
    client.cookies.set("access_token", access_token)
    response = await client.get(STAGES_URL, params={"pipeline_id": str(pipeline_b.id)})

    assert response.status_code == 200, response.text
    # Org A no debe ver stages de org B.
    assert response.json() == [], (
        "IDOR detectado: org A puede leer stages de org B a través de GET /stages"
    )


@pytest.mark.asyncio
async def test_list_stages_org_a_sees_own_stages(
    client: AsyncClient,
    access_token: str,
    pipeline_a: Pipeline,
    stage_a: Stage,
) -> None:
    """H-015 (happy path): Un usuario de org A sí ve sus propios stages."""
    client.cookies.set("access_token", access_token)
    response = await client.get(STAGES_URL, params={"pipeline_id": str(pipeline_a.id)})

    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(stage_a.id)


# ─── H-016: assigned_to cross-org ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_lead_assigned_to_other_org_user_rejected(
    client: AsyncClient,
    access_token: str,
    agent_b: User,
) -> None:
    """H-016: Crear un lead con assigned_to de otra org debe devolver 400."""
    client.cookies.set("access_token", access_token)
    response = await client.post(LEADS_URL, json={
        "first_name": "Cross",
        "last_name": "OrgLead",
        "assigned_to": str(agent_b.id),  # user pertenece a org B
    })
    assert response.status_code == 400, (
        f"H-016: Se esperaba 400 al asignar a usuario de otra org, se obtuvo {response.status_code}"
    )


@pytest.mark.asyncio
async def test_create_contact_assigned_to_other_org_user_rejected(
    client: AsyncClient,
    access_token: str,
    agent_b: User,
) -> None:
    """H-016: Crear un contacto con assigned_to de otra org debe devolver 400."""
    client.cookies.set("access_token", access_token)
    response = await client.post(CONTACTS_URL, json={
        "first_name": "Cross",
        "last_name": "OrgContact",
        "assigned_to": str(agent_b.id),  # user pertenece a org B
    })
    assert response.status_code == 400, (
        f"H-016: Se esperaba 400 al asignar a usuario de otra org, se obtuvo {response.status_code}"
    )


@pytest.mark.asyncio
async def test_supervisor_assign_lead_to_other_org_user_rejected(
    client: AsyncClient,
    lead_a: Lead,
    supervisor_a: User,
    agent_b: User,
) -> None:
    """H-016: PATCH /supervisor/leads/{id}/assign con user de otra org debe devolver 400."""
    token_a = create_access_token({"sub": str(supervisor_a.id)})
    client.cookies.set("access_token", token_a)

    response = await client.patch(
        f"{SUPERVISOR_URL}/leads/{lead_a.id}/assign",
        json={"assigned_to": str(agent_b.id)},  # user pertenece a org B
    )
    assert response.status_code == 400, (
        f"H-016: Se esperaba 400 al asignar a usuario de otra org, se obtuvo {response.status_code}"
    )


@pytest.mark.asyncio
async def test_create_lead_assigned_to_own_org_user_succeeds(
    client: AsyncClient,
    access_token: str,
    supervisor_a: User,
) -> None:
    """H-016 (happy path): assigned_to de la misma org es válido."""
    client.cookies.set("access_token", access_token)
    response = await client.post(LEADS_URL, json={
        "first_name": "Valid",
        "last_name": "Assignment",
        "assigned_to": str(supervisor_a.id),  # user pertenece a org A
    })
    assert response.status_code == 201, response.text


# ─── H-017: FKs de Deal cross-org ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_deal_with_contact_from_other_org_rejected(
    client: AsyncClient,
    access_token: str,
    stage_a: Stage,
    pipeline_a: Pipeline,
    contact_b: Contact,
) -> None:
    """H-017: Crear deal con contact_id de otra org debe devolver 400."""
    client.cookies.set("access_token", access_token)
    response = await client.post(DEALS_URL, json={
        "name": "Cross-org Deal",
        "contact_id": str(contact_b.id),  # contacto de org B
        "stage_id": str(stage_a.id),
        "pipeline_id": str(pipeline_a.id),
    })
    assert response.status_code == 400, (
        f"H-017: Se esperaba 400 con contact de otra org, se obtuvo {response.status_code}"
    )


@pytest.mark.asyncio
async def test_create_deal_with_stage_from_other_org_rejected(
    client: AsyncClient,
    access_token: str,
    contact_a: Contact,
    pipeline_a: Pipeline,
    stage_b: Stage,
    pipeline_b: Pipeline,
) -> None:
    """H-017: Crear deal con stage_id de otra org debe devolver 400."""
    client.cookies.set("access_token", access_token)
    response = await client.post(DEALS_URL, json={
        "name": "Cross-org Deal",
        "contact_id": str(contact_a.id),
        "stage_id": str(stage_b.id),       # stage de org B
        "pipeline_id": str(pipeline_b.id), # pipeline de org B
    })
    assert response.status_code == 400, (
        f"H-017: Se esperaba 400 con stage de otra org, se obtuvo {response.status_code}"
    )


@pytest.mark.asyncio
async def test_create_deal_all_same_org_succeeds(
    client: AsyncClient,
    access_token: str,
    contact_a: Contact,
    stage_a: Stage,
    pipeline_a: Pipeline,
) -> None:
    """H-017 (happy path): Deal con todos los recursos de la misma org es válido."""
    client.cookies.set("access_token", access_token)
    response = await client.post(DEALS_URL, json={
        "name": "Valid Deal",
        "contact_id": str(contact_a.id),
        "stage_id": str(stage_a.id),
        "pipeline_id": str(pipeline_a.id),
    })
    assert response.status_code == 201, response.text


# ─── H-022: conversión con stage/pipeline cross-org ──────────────────────────


@pytest.mark.asyncio
async def test_convert_lead_with_cross_org_stage_rejected(
    client: AsyncClient,
    access_token: str,
    lead_a: Lead,
    stage_b: Stage,
    pipeline_b: Pipeline,
) -> None:
    """H-022: Convertir lead con stage/pipeline de otra org debe devolver 400."""
    client.cookies.set("access_token", access_token)
    response = await client.post(
        CONVERSION_URL.format(lead_id=lead_a.id),
        json={
            "create_deal": True,
            "stage_id": str(stage_b.id),       # stage de org B
            "pipeline_id": str(pipeline_b.id), # pipeline de org B
        },
    )
    assert response.status_code == 400, (
        f"H-022: Se esperaba 400 al convertir con stage de otra org, se obtuvo {response.status_code}"
    )


@pytest.mark.asyncio
async def test_convert_lead_with_same_org_stage_succeeds(
    client: AsyncClient,
    access_token: str,
    lead_a: Lead,
    stage_a: Stage,
    pipeline_a: Pipeline,
) -> None:
    """H-022 (happy path): Conversión con stage de la misma org es válida."""
    client.cookies.set("access_token", access_token)
    response = await client.post(
        CONVERSION_URL.format(lead_id=lead_a.id),
        json={
            "create_deal": True,
            "stage_id": str(stage_a.id),
            "pipeline_id": str(pipeline_a.id),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["contact"] is not None
    assert data["deal"] is not None
