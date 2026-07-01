# HALLAZGOS — Auditoría Vortem CRM

> Formato: ID · Severidad · Ubicación · Impacto · Fix propuesto · Estado

---

---

> **Actualización 2026-06-28 — Repriorización por cambio de alcance**
>
> - H-001, H-002, H-006 → **DIFERIDOS**: el endpoint no está expuesto a internet. Reactivar obligatoriamente antes de exponer la app.
> - H-005 → **APARCADO**: puro VoiceHire, fuera de alcance actual.
> - H-004, H-007, H-011 → **SUBEN de prioridad**: el mismo motor de eventos alimenta los triggers nuevos.
> - H-015 a H-028 → nuevos hallazgos de la Fase 1b (nueva superficie).

---

## H-001 — 🔴 Crítico [DIFERIDO]: Secret del webhook con valor por defecto funcional y conocido

| Campo | Valor |
|-------|-------|
| **Severidad** | 🔴 Crítico |
| **Ubicación** | `backend/app/core/config.py:50` |
| **Estado** | Abierto |

**Descripción**

`VOICEHIRE_WEBHOOK_SECRET` tiene un valor por defecto hardcodeado (`"change-me-in-production"`). Si el operador no define la variable de entorno, la aplicación arranca con ese valor y lo acepta como secret válido. El mismo string aparece en los tests (`backend/tests/test_webhooks.py:18`), por lo que cualquier persona con acceso al repositorio puede enviar webhooks fraudulentos a cualquier instancia no configurada.

```python
# config.py:50 — ACTUAL (vulnerable)
VOICEHIRE_WEBHOOK_SECRET: str = "change-me-in-production"
```

**Fix propuesto**

Requerir la variable explícitamente (sin default) y añadir un validador que rechace valores cortos o conocidos:

```python
# config.py — PROPUESTO
VOICEHIRE_WEBHOOK_SECRET: str = Field(
    ...,
    min_length=32,
    description="Shared secret para autenticar webhooks entrantes de VoiceHire.",
)

@field_validator("VOICEHIRE_WEBHOOK_SECRET")
@classmethod
def validate_webhook_secret(cls, v: str) -> str:
    insecure = {"change-me-in-production", "secret", ""}
    if v in insecure:
        raise ValueError("VOICEHIRE_WEBHOOK_SECRET no puede ser un valor por defecto.")
    return v
```

Los tests deben generar su propio secret de 32 chars y sobreescribir `settings.VOICEHIRE_WEBHOOK_SECRET` en el fixture de configuración.

---

## H-002 — 🔴 Crítico [DIFERIDO]: Timing oracle en la verificación del shared secret

| Campo | Valor |
|-------|-------|
| **Severidad** | 🔴 Crítico |
| **Ubicación** | `backend/app/api/v1/webhooks.py:26` |
| **Estado** | Abierto |

**Descripción**

La comparación del header `X-VoiceHire-Secret` contra el secret configurado usa el operador `!=` de Python, que hace una comparación de strings byte a byte y devuelve en cuanto encuentra una diferencia. Un atacante puede medir el tiempo de respuesta para adivinar el secret byte a byte (timing side-channel).

```python
# webhooks.py:26 — ACTUAL (vulnerable)
if x_voicehire_secret != settings.VOICEHIRE_WEBHOOK_SECRET:
```

**Fix propuesto**

Usar `hmac.compare_digest`, que garantiza tiempo constante:

```python
# webhooks.py — PROPUESTO
import hmac

def _verify_voicehire_secret(
    x_voicehire_secret: str | None = Header(default=None),
) -> None:
    provided = x_voicehire_secret or ""
    expected = settings.VOICEHIRE_WEBHOOK_SECRET
    if not hmac.compare_digest(provided.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing VoiceHire secret.",
        )
```

---

## H-003 — 🟠 Alto: Campo `event` del webhook sin validación de enum

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟠 Alto |
| **Ubicación** | `backend/app/schemas/webhook.py:12` |
| **Estado** | Abierto |

**Descripción**

El campo `event` es `str` libre. El CRM acepta cualquier string (p. ej. `"hacked"`, `""`, cadenas de 10 000 caracteres) sin rechazarlo. El código de la capa de servicio usa `payload.event` para construir el `body` de la `Activity` sin validar su valor, lo que puede crear registros con datos arbitrarios.

Adicionalmente, la lógica de publicación de eventos en `webhooks.py:56-62` depende del campo `status` (no de `event`) para decidir si publicar `LEAD_QUALIFIED`, por lo que el valor de `event` es actualmente decorativo pero puede volverse funcional en el futuro.

```python
# webhook.py:12 — ACTUAL
event: str  # 'call_completed', 'lead_qualified', 'lead_discarded'
```

**Fix propuesto**

```python
# schemas/webhook.py — PROPUESTO
from typing import Literal

VoiceHireEvent = Literal["call_completed", "lead_qualified", "lead_discarded"]

class VoiceHireWebhookPayload(BaseModel):
    lead_id: uuid.UUID
    event: VoiceHireEvent
    status: str | None = None
    voicehire_data: dict = {}
    campaign_id: uuid.UUID | None = None
```

---

## H-004 — 🟠 Alto: Webhook no idempotente — reintentos duplican registros `Activity`

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟠 Alto |
| **Ubicación** | `backend/app/services/webhook_service.py:62-69` |
| **Estado** | Abierto |

**Descripción**

Cada llamada al endpoint webhook crea un nuevo registro `Activity(type=voicehire_call)` sin verificar si ya existe uno para ese mismo evento. Si VoiceHire reenvía el webhook por timeout o error de red, el lead acumulará activities duplicadas. El merge de `voicehire_data` y el set de `campaign_id` son idempotentes, pero la creación de `Activity` no lo es.

```python
# webhook_service.py:62 — ACTUAL (no idempotente)
activity = Activity(
    organization_id=organization_id,
    type=ActivityType.voicehire_call,
    lead_id=lead.id,
    body=f"VoiceHire event: {payload.event}",
    metadata_=payload.voicehire_data,
)
session.add(activity)
```

**Fix propuesto**

Añadir un campo `idempotency_key` (UUID de la llamada VoiceHire) al payload y hacer upsert o skip si ya existe:

```python
# schemas/webhook.py — añadir campo
class VoiceHireWebhookPayload(BaseModel):
    ...
    idempotency_key: uuid.UUID | None = None  # ID único de la llamada VoiceHire

# webhook_service.py — PROPUESTO
from sqlalchemy import select

if payload.idempotency_key:
    existing = await session.execute(
        select(Activity).where(
            Activity.lead_id == lead.id,
            Activity.metadata_["idempotency_key"].astext == str(payload.idempotency_key),
        )
    )
    if existing.scalar_one_or_none() is not None:
        logger.info("webhook_duplicate_skipped", idempotency_key=str(payload.idempotency_key))
        return lead  # Skip — ya procesado

activity = Activity(
    ...
    metadata_={**payload.voicehire_data, "idempotency_key": str(payload.idempotency_key)},
)
```

> Alternativa: que VoiceHire siempre envíe el ID de la llamada en `voicehire_data` y usar ese campo como clave de idempotencia sin modificar el schema.

---

## H-005 — 🟠 Alto [APARCADO — fuera de alcance actual]: Sin firma HMAC del body completo del webhook

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟠 Alto |
| **Ubicación** | `backend/app/api/v1/webhooks.py:22-30` |
| **Estado** | Abierto |

**Descripción**

La autenticación del webhook solo verifica un shared secret en un header HTTP. Esto no protege contra:
- **Replay attacks**: un attacker que captura un request válido puede reenviarlo.
- **Tamper attacks**: en redes internas sin TLS, el body puede modificarse sin invalidar el header.

El estándar de la industria (GitHub, Stripe, Twilio) es firmar el body con HMAC-SHA256 y enviar la firma en un header (`X-Hub-Signature-256`, `Stripe-Signature`, etc.).

**Fix propuesto**

Añadir verificación de firma HMAC del raw body, o al menos documentar explícitamente por qué el modelo de amenaza actual no requiere firma de body (por ejemplo, si toda la comunicación ocurre en red privada con TLS mutuo).

```python
# webhooks.py — PROPUESTO (con firma HMAC)
import hashlib, hmac

async def _verify_voicehire_signature(
    request: Request,
    x_voicehire_signature: str | None = Header(default=None),
) -> None:
    body = await request.body()
    expected_sig = hmac.new(
        settings.VOICEHIRE_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    provided = (x_voicehire_signature or "").removeprefix("sha256=")
    if not hmac.compare_digest(provided, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid signature.")
```

> Decisión requerida: ¿el modelo de amenaza justifica la firma completa? Registrar en DECISIONES.md.

---

## H-006 — 🟡 Medio [DIFERIDO]: `VOICEHIRE_WEBHOOK_SECRET` ausente de `.env.example`

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `.env.example` (ausencia) |
| **Estado** | Abierto |

**Descripción**

La variable `VOICEHIRE_WEBHOOK_SECRET` no aparece en `.env.example`. Un operador que configure el sistema desde cero no sabrá que debe definirla, y si la aplicación tiene un default (ver H-001), arrancará sin error con el valor inseguro.

**Fix propuesto**

```bash
# .env.example — añadir en sección de integraciones
# Secret compartido con VoiceHire para autenticar webhooks entrantes.
# Generar con: python -c "import secrets; print(secrets.token_urlsafe(32))"
VOICEHIRE_WEBHOOK_SECRET=CHANGE_ME_GENERATE_WITH_SECRETS_MODULE
```

---

## H-007 — 🟠 Alto: Ventana de pérdida de eventos entre commit de negocio y `publish()`

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟠 Alto |
| **Ubicación** | `backend/app/api/v1/webhooks.py` + `backend/app/events/publisher.py` |
| **Estado** | ✅ Resuelto — 2026-06-30 (D-009 opción B) |

**Descripción**

El flujo original tenía tres commits separados en la misma sesión:

```
1. await session.commit()        # commit negocio (lead + activity)
2. await publish(LEAD_QUALIFIED) # si qualified: commit evento 1 (segunda transacción)
3. await publish(VOICEHIRE_CALL_COMPLETED) # siempre: commit evento 2 (tercera transacción)
```

Si el proceso moría entre el commit 1 y los commits 2/3, los datos de negocio quedaban persistidos pero los eventos nunca se insertaban en la tabla `events`. El worker drena `events` al arrancar, pero si los eventos nunca se insertaron, no hay nada que drenar.

**Fix aplicado — outbox pattern (D-009, opción B)**

`publisher.py` ya no hace `session.commit()` interno. El evento se flushea dentro de la transacción del llamador. El llamador hace un único `session.commit()` que incluye negocio + evento. pg_notify es transaccional en PostgreSQL y se entrega al worker cuando ese commit ocurre.

Nuevo patrón en todos los endpoints:
```python
# ANTES (vulnerable): negocio commit → publish (segunda transacción)
await session.commit()
await publish(session, ...)   # commit interno en publisher.py

# DESPUÉS (atómico): publish flushea en la transacción abierta → commit único
await publish(session, ...)   # solo flush + pg_notify
await session.commit()        # un único commit: negocio + evento
```

**Archivos modificados**: `publisher.py`, `webhooks.py`, `leads.py`, `contacts.py`, `deals.py`, `pipelines.py`, `supervisor.py`

**Tests añadidos** (`tests/test_outbox.py`) — 107/107 verdes:
- `test_outbox_publish_failure_rolls_back_lead_creation` — si publish() lanza, el lead NO queda en BD
- `test_outbox_webhook_publish_failure_rolls_back_lead_status` — si publish() lanza en webhook, el status NO cambia
- `test_outbox_webhook_both_events_committed_atomically` — verifica que LEAD_QUALIFIED y VOICEHIRE_CALL_COMPLETED se persisten juntos

**Fixes en el harness de test (2026-06-30):**
- `tests/conftest.py`: `_override_get_session` añade `try/except Exception: rollback; raise` para espejo fiel de `get_session()` de producción.
- `tests/conftest.py`: `ASGITransport(raise_app_exceptions=False)` — Starlette re-lanza excepciones no manejadas después de enviar el 500; esta opción hace que httpx devuelva la respuesta en lugar de propagar la excepción al test.
- `tests/test_outbox.py`: `lead_id` capturado antes del request para evitar `MissingGreenlet` al acceder a atributos de objetos expirados por el rollback.

**Fix secundario (2026-06-30):**
- `app/core/logging.py`: `ProcessorFormatter` corregido — `shared_processors` movido a `foreign_pre_chain`; `remove_processors_meta` eliminaba `_record` antes de que `add_logger_name` pudiera leerlo, causando `'NoneType' object has no attribute 'name'`.

---

## H-008 — 🟡 Medio: Sin pipeline de CI/CD

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | Raíz del repo (ausencia de `.github/workflows/`) |
| **Estado** | Abierto |

**Descripción**

Los tests solo se ejecutan manualmente (documentado como checklist de cierre de sesión en `README.md`). No hay automatización que los ejecute en PR o en push. Un merge con tests rotos depende de disciplina manual.

**Fix propuesto**

Añadir `.github/workflows/ci.yml` con job `pytest -v` ejecutado en un contenedor Docker similar al de desarrollo.

---

## H-009 — 🟡 Medio: Bootstrap crea admin global sin organización (workaround manual documentado)

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/api/v1/setup.py` + `DEPLOYMENT.md` (Step 5b) |
| **Estado** | ✅ Resuelto — 2026-06-30 (D-010) |

**Descripción**

El endpoint `POST /api/v1/setup` crea un `User(is_global_admin=True, organization_id=None)`. Este usuario no puede operar ningún endpoint de negocio (leads, contacts, deals) porque todos requieren `organization_id`. El `DEPLOYMENT.md` documentaba como workaround ejecutar un `INSERT SQL` manual con un hash bcrypt hardcodeado.

Esto era frágil: el hash bcrypt podía quedar desactualizado, y un operador sin conocimientos de SQL podía dejar el sistema inutilizable.

**Fix implementado (2026-06-30)**

CLI script `backend/app/cli/create_admin.py` invocable como:
```
docker compose exec -it backend python -m app.cli.create_admin
```

- Solicita email, nombre, org name y contraseña de forma interactiva (contraseña oculta con `getpass`).
- Hashea la contraseña vía `hash_password()` de la app — nunca expone el hash al operador.
- Reutiliza la org existente si ya fue creada por `POST /api/v1/setup`, o crea una nueva.
- Protección: si ya existe algún usuario con `organization_id IS NOT NULL`, rechaza la ejecución.
- Capa de lógica (`create_org_admin`) separada del CLI entry point — testeable sin subprocess.

**Tests:** `tests/test_cli_create_admin.py` — 3 tests, 110/110 suite verde.

---

## H-010 — 🟡 Medio: `voicehire_data` sin límite de tamaño ni estructura

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/schemas/webhook.py:14` |
| **Estado** | Abierto |

**Descripción**

El campo `voicehire_data: dict = {}` acepta cualquier dict JSON sin restricción de tamaño, profundidad o claves. Un payload malicioso o un bug en VoiceHire puede enviar megabytes de datos, saturar la columna JSONB y degradar queries sobre la tabla `leads`.

**Fix propuesto**

```python
from pydantic import field_validator

class VoiceHireWebhookPayload(BaseModel):
    ...
    voicehire_data: dict = {}

    @field_validator("voicehire_data")
    @classmethod
    def validate_voicehire_data(cls, v: dict) -> dict:
        import json
        if len(json.dumps(v)) > 64_000:  # 64 KB
            raise ValueError("voicehire_data excede el tamaño máximo permitido.")
        return v
```

---

## H-011 — 🟡 Medio: `LEAD_QUALIFIED` se republica en reintentos si el lead ya estaba calificado

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/api/v1/webhooks.py:56-62` |
| **Estado** | Abierto |

**Descripción**

La condición para publicar `LEAD_QUALIFIED` comprueba el status del lead DESPUÉS del procesamiento:

```python
if lead.status == LeadStatus.qualified:
    await publish(session, EventType.LEAD_QUALIFIED, ...)
```

Si VoiceHire reenvía el webhook porque no recibió respuesta 200 (y el lead ya estaba `qualified` de la primera llamada), el evento se publica de nuevo, creando una segunda ronda de notificaciones a supervisores.

**Fix propuesto**

Capturar el status anterior antes de mutar y comparar:

```python
# webhook_service.py — PROPUESTO
status_before = lead.status
# ... mutaciones ...
lead.status_changed = (lead.status != status_before)  # campo transitorio no persistido
```

```python
# webhooks.py — PROPUESTO
if lead.status == LeadStatus.qualified and status_before != LeadStatus.qualified:
    await publish(session, EventType.LEAD_QUALIFIED, ...)
```

---

## H-012 — 🟡 Medio: `X-Request-ID` del cliente se propaga a logs sin sanitizar

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/main.py:57` |
| **Estado** | Abierto |

**Descripción**

```python
request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
```

Un cliente puede inyectar un `request_id` arbitrario (cadenas largas, caracteres de control, secuencias de escape JSON) que se propagará a todos los registros de log estructurado de esa request.

**Fix propuesto**

Validar que el header sea un UUID antes de usarlo, o ignorarlo y siempre generar uno interno:

```python
import re
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

raw = request.headers.get("X-Request-ID", "")
request_id = raw if _UUID_RE.match(raw) else str(uuid.uuid4())
```

---

## H-013 — 🟡 Medio: Sin tests en el frontend

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `frontend/` (ausencia de suite de tests) |
| **Estado** | Abierto |

**Descripción**

No hay ninguna suite de tests en la capa Next.js (ni Vitest, ni Jest, ni Playwright). Los hooks de data fetching (`useLeads`, `useAuth`, etc.) y los formularios son los más críticos de probar.

**Fix propuesto**

Añadir Vitest + React Testing Library para hooks y componentes críticos. Playwright para tests E2E del flujo de webhook (enviar evento → verificar UI actualizada).

---

## H-014 — 🟡 Medio: `campaign_id` sin FK constraint ni documentación de intención (DIFERIDO)

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/models/lead.py:59` |
| **Estado** | Abierto |

**Descripción**

```python
# lead.py:59 — comentario explica la ausencia de FK
# Plain UUID — no FK constraint; Pipeline module wires this in a future phase.
campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
```

El comentario indica que es intencional, pero no hay ninguna validación en el webhook service que verifique que el `campaign_id` recibido de VoiceHire sea un UUID con formato válido (aunque Pydantic ya lo valida como `uuid.UUID`). El riesgo real es que un campaign_id inválido quede almacenado indefinidamente sin referencia.

**Fix propuesto**

Documentar en DECISIONES.md que `campaign_id` es una referencia suave a un sistema externo (VoiceHire) y que la integridad referencial es responsabilidad de VoiceHire. Añadir nota en el schema de webhook.

---

# HALLAZGOS FASE 1b — Nueva superficie (2026-06-28)

---

## H-015 — 🔴 Crítico: IDOR en `GET /stages` — cualquier usuario lee stages de otra organización

| Campo | Valor |
|-------|-------|
| **Severidad** | 🔴 Crítico |
| **Ubicación** | `backend/app/services/stage_service.py:53-62` + `backend/app/api/v1/stages.py:36-47` |
| **Estado** | Abierto |

**Descripción**

`GET /api/v1/stages?pipeline_id=X` no filtra por `organization_id`. Cualquier usuario autenticado en la org A puede pasar el `pipeline_id` de la org B (UUIDs predecibles si se filtran de otra respuesta) y leer todos sus stages.

```python
# stage_service.py:53 — ACTUAL (vulnerable)
async def list_stages(session: AsyncSession, pipeline_id: uuid.UUID) -> list[Stage]:
    result = await session.execute(
        select(Stage).where(Stage.pipeline_id == pipeline_id)  # sin org filter
    )
```

```python
# stages.py:36 — endpoint no pasa org_id al servicio
stages = await stage_service.list_stages(session, pipeline_id)  # sin org_id
```

**Fix propuesto**

```python
# stage_service.py — PROPUESTO
async def list_stages(
    session: AsyncSession,
    organization_id: uuid.UUID,
    pipeline_id: uuid.UUID,
) -> list[Stage]:
    result = await session.execute(
        select(Stage).where(
            Stage.pipeline_id == pipeline_id,
            Stage.organization_id == organization_id,  # añadir filtro
        ).order_by(Stage.order.asc())
    )

# stages.py — pasar org_id
org_id = get_current_org_id(current_user)
stages = await stage_service.list_stages(session, org_id, pipeline_id)
```

---

## H-016 — 🟠 Alto: `assigned_to` en leads/contacts/deals no se valida contra la organización del token

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟠 Alto |
| **Ubicación** | `backend/app/schemas/lead.py:21`, `backend/app/schemas/contact.py:21`, `backend/app/schemas/deal.py:19` |
| **Estado** | Abierto |

**Descripción**

Los campos `assigned_to` en `LeadCreate`, `ContactCreate` y `DealCreate` aceptan cualquier UUID sin verificar que el usuario target pertenezca a la misma organización. Un admin de org A puede asignar un lead a un usuario de org B.

Ninguno de los servicios (`lead_service.create_lead`, `contact_service.create_contact`, `deal_service.create_deal`) hace un `SELECT User WHERE id=assigned_to AND organization_id=org_id` antes de escribir.

**Fix propuesto**

En los servicios de creación y actualización, añadir una validación antes del flush:

```python
# Ejemplo para lead_service.create_lead
if data.assigned_to is not None:
    user_result = await session.execute(
        select(User).where(
            User.id == data.assigned_to,
            User.organization_id == organization_id,
            User.is_active.is_(True),
        )
    )
    if user_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="assigned_to user not found in this organization.")
```

Aplica igual a `supervisor_service.assign_lead`.

---

## H-017 — 🟠 Alto: `DealCreate.contact_id`/`stage_id`/`pipeline_id` no se validan contra la organización

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟠 Alto |
| **Ubicación** | `backend/app/services/deal_service.py:17-27` |
| **Estado** | Abierto |

**Descripción**

`deal_service.create_deal` asigna `organization_id` del token al deal, pero no verifica que `contact_id`, `stage_id` ni `pipeline_id` pertenezcan a esa organización. Una org A podría crear un deal que referencie el contact o la etapa de org B.

Lo mismo aplica en `conversion_service.convert_lead` cuando `create_deal=True`: el `stage_id` y `pipeline_id` no se validan.

```python
# deal_service.py:23 — ACTUAL (sin validación)
deal = Deal(organization_id=organization_id, **data.model_dump())
```

**Fix propuesto**

```python
# deal_service.py — PROPUESTO
async def create_deal(session, organization_id, data):
    # Validar que contact, stage y pipeline pertenezcan a la org
    for model, fk_id, name in [
        (Contact, data.contact_id, "contact_id"),
        (Stage, data.stage_id, "stage_id"),
        (Pipeline, data.pipeline_id, "pipeline_id"),
    ]:
        res = await session.execute(
            select(model).where(model.id == fk_id, model.organization_id == organization_id)
        )
        if res.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail=f"{name} not found in this organization.")
    ...
```

---

## H-018 — 🟠 Alto: Sin validación de formato en `email` y `phone` — crítico para importación CSV

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟠 Alto |
| **Ubicación** | `backend/app/schemas/lead.py:15-16`, `backend/app/schemas/contact.py:14-15` |
| **Estado** | Abierto |

**Descripción**

Los campos `email` y `phone` son `str | None` sin ninguna validación de formato. Para la importación de CSV —donde la validación por fila es un requisito explícito— cualquier string malformado quedaría almacenado. El error se descubrirá tarde (al intentar usar el email para enviar algo) en lugar de al importar.

```python
# schemas/lead.py:15-16 — ACTUAL
phone: str | None = None
email: str | None = None
```

**Fix propuesto**

```python
# schemas compartido (o por entidad) — PROPUESTO
from pydantic import EmailStr, field_validator
import re

_PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,20}$")

class LeadCreate(BaseModel):
    email: EmailStr | None = None  # Pydantic valida RFC 5322
    phone: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None and not _PHONE_RE.match(v.strip()):
            raise ValueError("Formato de teléfono inválido.")
        return v.strip() if v else None
```

Requiere `pydantic[email]` (ya es dependencia de Pydantic v2).

---

## H-019 — 🟠 Alto: Importación de CSV completamente ausente

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟠 Alto |
| **Ubicación** | Funcionalidad inexistente |
| **Estado** | Abierto — a construir |

**Descripción**

No existe ningún endpoint, servicio ni modelo para importar bases de datos de clientes desde CSV. Es una de las 4 capacidades nuevas requeridas.

**Alcance de lo que falta construir**

1. `POST /api/v1/leads/import` — `multipart/form-data`, campo `file: UploadFile`
2. Parser CSV con detección de encoding (UTF-8, UTF-8-BOM, Latin-1)
3. Validación por fila: `first_name`, `last_name` obligatorios; `email` y `phone` con formato
4. Sanitización de CSV injection: celdas que empiecen por `= + - @` se prefijan con `'`
5. Deduplicación: definir clave (ver D-006 en DECISIONES.md)
6. Comportamiento en fallo parcial (ver D-007)
7. Bulk insert en lotes de N filas (no N transacciones individuales)
8. Límite de tamaño: max 10 MB / 50 000 filas (configurable)
9. Respuesta: `{imported: N, skipped: N, failed: [{row, reason}]}`
10. Evento `LEADS_IMPORTED` publicado al finalizar (para triggers futuros)

---

## H-020 — 🟠 Alto: Sin estados/categorías personalizados por organización

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟠 Alto |
| **Ubicación** | `backend/app/models/lead.py:15-20`, `backend/app/models/contact.py:15-18` |
| **Estado** | Abierto — a construir |

**Descripción**

`LeadStatus` y `ContactStatus` son enums de Python/PostgreSQL hardcodeados. Ninguna organización puede añadir, renombrar ni eliminar estados. La columna `Contact.tags JSONB` es freeform pero:
- `Lead` no tiene `tags` ni `custom_fields`
- No hay validación de los valores de tags contra un catálogo por org
- No hay mecanismo para asociar acciones a esos estados/categorías

**Alcance de lo que falta construir**

1. Tabla `lead_labels` (o `custom_tags`): `{id, org_id, name, color, description, is_active}`
2. Tabla `lead_label_assignments`: `{lead_id, label_id}` — relación N:M
3. Migración que deje las etiquetas como texto libre en `Lead.tags JSONB` (igual que `Contact`)
4. APIs: CRUD de etiquetas + asignar/desasignar etiquetas a un lead
5. O alternativamente: extender `Lead` con `tags JSONB` y un endpoint de gestión de tags permitidas por org

> Decisión requerida: modelo de tags libres vs. catálogo validado por org. Ver D-008.

---

## H-021 — 🟠 Alto: Motor de triggers (estado → acción automática) inexistente

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟠 Alto |
| **Ubicación** | Funcionalidad inexistente |
| **Estado** | Abierto — a construir |

**Descripción**

No existe ningún mecanismo configurable para que una organización defina "cuando un lead entra en el estado/categoría X, ejecutar la acción Y". El worker tiene handlers hardcodeados en `_HANDLERS` que no son configurables por org ni por usuario.

**Alcance de lo que falta construir**

1. Tabla `triggers`: `{id, org_id, name, entity_type, trigger_event, condition_json, action_type, action_config_json, is_active}`
2. Al cambiar el estado/etiqueta de un lead/contact, publicar evento `LEAD_LABEL_CHANGED` / `LEAD_STATUS_CHANGED`
3. Handler en el worker: leer triggers activos de la org → evaluar condición → ejecutar acción
4. Acciones iniciales soportadas: crear notificación, asignar a usuario, cambiar estado
5. Idempotencia: registrar ejecuciones en `trigger_executions` `{trigger_id, entity_id, event_id, executed_at, result}` — para no re-disparar si el evento se reprocesa (cierra H-004 y H-011 en el contexto de triggers)
6. Observabilidad: la tabla `trigger_executions` sirve como log de auditoría

---

## H-022 — 🟡 Medio: `conversion_service` no valida `stage_id`/`pipeline_id` contra la organización

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/services/conversion_service.py:93-104` |
| **Estado** | Abierto |

**Descripción**

Cuando `create_deal=True` en la conversión de lead, el `stage_id` y `pipeline_id` del request se usan directamente sin verificar que pertenezcan a la misma organización. Es el mismo patrón que H-017 pero en otro servicio.

```python
# conversion_service.py:93 — sin validación de org
deal = Deal(
    organization_id=organization_id,
    stage_id=stage_id,     # no validado
    pipeline_id=pipeline_id,  # no validado
    ...
)
```

**Fix propuesto**

Reutilizar la misma función de validación de FK cruzada propuesta en H-017.

---

## H-023 — 🟡 Medio: Sin bulk insert — importación CSV de N filas haría N transacciones individuales

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/services/lead_service.py:17-39` (patrón de inserción) |
| **Estado** | Abierto |

**Descripción**

El patrón actual crea un `Lead`, hace `flush()` y espera que el endpoint haga `commit()`. Para importar 10 000 filas así se generarían 10 000 flushes en una sola transacción (riesgo de OOM en el session) o 10 000 commits individuales (extremadamente lento).

**Fix propuesto**

Usar `session.execute(insert(Lead).values([...]))` en lotes de 500-1 000 filas, con un único commit por lote. SQLAlchemy Core soporta bulk insert sin cargar los objetos en memoria.

```python
from sqlalchemy.dialects.postgresql import insert

BATCH_SIZE = 500

async def bulk_create_leads(session, organization_id, rows: list[dict]) -> int:
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        await session.execute(insert(Lead), [{"organization_id": organization_id, **r} for r in batch])
        await session.commit()
    return len(rows)
```

---

## H-024 — 🟡 Medio: `LeadCreate.voicehire_data` es editable por el usuario en creación manual

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/schemas/lead.py:22` |
| **Estado** | Abierto |

**Descripción**

```python
# schemas/lead.py:22
voicehire_data: dict = {}
```

Un usuario puede setear `voicehire_data` al crear un lead manualmente, inyectando datos arbitrarios en un campo diseñado para recibir datos de VoiceHire. En el nuevo contexto (sin VoiceHire en el alcance), este campo debería ser no editable en creación manual.

**Fix propuesto**

Eliminar `voicehire_data` de `LeadCreate`. El campo solo debe ser escribible por el endpoint de webhook. En `lead_service.create_lead`, no incluir el campo (se inicializa con `default=dict` en el modelo).

---

## H-025 — 🟡 Medio: `list_leads`/`list_contacts` sin filtros — inviable con bases grandes

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/services/lead_service.py:42-56`, `backend/app/services/contact_service.py:42-56` |
| **Estado** | Abierto |

**Descripción**

Los endpoints de listado solo exponen `skip` y `limit`. No hay filtro por nombre, email, teléfono, estado, fuente ni etiqueta. Con 10 000 registros importados vía CSV, un usuario que busca un lead específico tendría que paginar manualmente.

**Fix propuesto**

Añadir parámetros de query opcionales:

```python
# leads.py — PROPUESTO
async def list_leads(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,   # búsqueda en first_name, last_name, email, phone
    status: LeadStatus | None = None,
    source: LeadSource | None = None,
    assigned_to: uuid.UUID | None = None,
    ...
)
```

Y en el servicio, construir el WHERE dinámicamente con `and_(*filters)`.

---

## H-026 — 🟡 Medio: Sin índice en `leads.email` y `leads.phone` — búsqueda de duplicados será lenta

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/alembic/versions/0002_contacts_leads.py` |
| **Estado** | Abierto |

**Descripción**

La tabla `leads` no tiene índice en `email` ni en `phone`. Para detectar duplicados durante la importación de CSV (que puede involucrar decenas de miles de filas), una query `WHERE organization_id = X AND email = Y` haría un seq scan sobre toda la tabla de la org.

**Fix propuesto**

Migración nueva:

```sql
CREATE INDEX ix_leads_org_email ON leads (organization_id, email) WHERE email IS NOT NULL;
CREATE INDEX ix_leads_org_phone ON leads (organization_id, phone) WHERE phone IS NOT NULL;
```

---

## H-027 — 🟡 Medio: `LeadCreate` no tiene `tags`/`custom_fields` — asimetría con `Contact`

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/models/lead.py`, `backend/app/schemas/lead.py` |
| **Estado** | Abierto |

**Descripción**

`Contact` tiene `tags: JSONB` y `custom_fields: JSONB`. `Lead` no tiene ninguno de los dos. Para implementar estados/categorías personalizados en leads (H-020), el modelo de datos de `Lead` necesita extenderse.

**Fix propuesto**

Migración que añade:

```sql
ALTER TABLE leads ADD COLUMN tags JSONB NOT NULL DEFAULT '[]';
ALTER TABLE leads ADD COLUMN custom_fields JSONB NOT NULL DEFAULT '{}';
```

Y actualizar el modelo SQLAlchemy y los schemas Pydantic correspondientemente.

---

## H-028 — 🟡 Medio: `DealCreate.currency` sin validación ISO 4217

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/schemas/deal.py:18` |
| **Estado** | Abierto |

**Descripción**

`currency: str = "USD"` acepta cualquier string. Un valor inválido (p. ej. `"DOLAR"`, `""`) quedaría almacenado, lo que rompería cualquier lógica de conversión o reporte que asuma ISO 4217.

**Fix propuesto**

```python
from pydantic import field_validator

@field_validator("currency")
@classmethod
def validate_currency(cls, v: str) -> str:
    v = v.strip().upper()
    if len(v) != 3 or not v.isalpha():
        raise ValueError("currency debe ser un código ISO 4217 de 3 letras (ej: USD, EUR, COP).")
    return v
```

---

# HALLAZGOS ÉPICA V — Verticales de negocio (2026-07-01)

---

## H-029 — 🟡 Medio: Concepto de "vertical" ausente en el modelo de Organization

| Campo | Valor |
|-------|-------|
| **Severidad** | 🟡 Medio |
| **Ubicación** | `backend/app/models/organization.py`, `backend/alembic/versions/` |
| **Estado** | ✅ Resuelto — 2026-07-01 |

**Descripción**

El modelo `Organization` no tenía ningún concepto de tipo de negocio ("vertical"). Sin este campo, el CRM no puede adaptar terminología ni pantallas según el sector del cliente (veterinaria, inmobiliaria, etc.). La agencia no tenía forma de marcar una org como perteneciente a una vertical específica, ni de proteger ese campo de modificaciones por parte del propio cliente.

**Fix implementado**

- Migración `0005_verticals.py`: enum PostgreSQL `org_vertical ('generic', 'veterinary')` + columna `organizations.vertical NOT NULL DEFAULT 'generic'`
- Enum `OrgVertical` en `models/organization.py` con `create_type=False` (tipo creado por la migración)
- Campo `vertical` en `OrganizationResponse` schema
- `SetupRequest` acepta `vertical` opcional (default `generic`)
- `create_org_admin()` CLI acepta `vertical` opcional (default `generic`)
- Nuevo endpoint `PATCH /api/v1/organizations/{org_id}/vertical` — solo `is_global_admin=True`; usuarios normales reciben 403
- 8 tests en `tests/test_verticals.py`; suite completa: **118/118 verdes**
