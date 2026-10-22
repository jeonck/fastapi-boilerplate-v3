# 데이터 설계 가이드 (FastAPI + SQLAlchemy)

관계형 DB와 비즈니스 로직을 다루는 백엔드에서 프로덕션 장애로 이어지기 쉬운 설계 함정 6가지와, 이 보일러플레이트(FastAPI · Pydantic v2 · SQLAlchemy 2.0)에서의 적용 방법을 정리합니다.

FastAPI는 `async def`로 요청을 빠르게 동시에 받아내기 때문에, 동시성·무결성 문제가 오히려 더 빨리 드러납니다. 핵심 원칙은 하나입니다.

> **잘못된 데이터가 들어올 길은 Python 코드가 아니라 DB 스키마와 제약 조건에서 막는다.**

| # | 주제 | 이 보일러플레이트 |
|---|---|---|
| 1 | NULL의 의미 분리 | 📘 가이드 |
| 2 | 비템포럴(Bitemporal) 이력 | 📘 가이드 |
| 3 | 금액은 `Decimal`, 환율은 이벤트 시점 스냅샷 | ✅ **적용됨** (`Item.price`) + 📘 스냅샷 가이드 |
| 4 | 미래 일정은 벽시계 시간 + 타임존 | 📘 가이드 |
| 5 | 소프트 딜리트와 조건부 유니크 | 📘 가이드 |
| 6 | 비즈니스 규칙의 DB 제약 + 409 | ✅ **적용됨** (`uq_items_name`, `IntegrityError → 409`) |

---

## 1. NULL의 의미 분리 — 상태는 Enum으로 명시

**문제.** `paid_at: datetime | None`만 있으면 `NULL`이 "아직 처리 전"인지, "실패"인지, "해당 없음"인지 알 수 없습니다. 이유가 다른 "값 없음"이 한 컬럼에 섞입니다.

**방법.** 생애주기를 `Enum` 상태 컬럼으로 분리하고, 상태와 나머지 컬럼의 조합을 **DB CHECK 제약**으로 강제합니다. Pydantic 검증은 API 입구에서 빨리 실패시키는 보조 수단입니다.

```python
import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column


class PayoutStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"


class Payout(Base):
    __tablename__ = "payouts"
    __table_args__ = (
        # paid 일 때만, 그리고 반드시 paid_at 이 있다
        CheckConstraint("(status = 'paid') = (paid_at IS NOT NULL)", name="ck_payouts_paid_at"),
        # failed 일 때만, 그리고 반드시 실패 사유가 있다
        CheckConstraint(
            "(status = 'failed') = (failure_reason IS NOT NULL)", name="ck_payouts_failure"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[PayoutStatus] = mapped_column(
        # values_callable: Enum 이름(PAID)이 아니라 값(paid)을 저장 → CHECK 문과 일치
        SAEnum(PayoutStatus, name="payout_status",
               values_callable=lambda e: [m.value for m in e]),
        default=PayoutStatus.PENDING,
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(String(200))
```

```python
from pydantic import BaseModel, model_validator


class PayoutRead(BaseModel):
    status: PayoutStatus
    paid_at: datetime | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def check_consistency(self):
        if (self.status == PayoutStatus.PAID) != (self.paid_at is not None):
            raise ValueError("paid_at must be set if and only if status is 'paid'")
        return self
```

**FastAPI 특유의 함정: PATCH의 "안 보냄" vs "null로 지움".** `UserUpdate`처럼 전부 `Optional`인 수정 스키마에서 `{"full_name": null}`(지우기)과 필드 생략(유지)을 구분하려면 `model_dump(exclude_unset=True)`를 써야 합니다. `model_dump()`는 둘 다 `None`으로 만들어 의도치 않게 값을 지웁니다.

---

## 2. 비템포럴(Bitemporal) 데이터 — 덮어쓰지 말고 쌓기

**문제.** 수수료율·계약 조건·요금제처럼 "언제부터 유효했는가"가 중요한 데이터를 `UPDATE ... SET rate = ?, updated_at = now()`로 덮어쓰면, 소급 정정 시 과거 정산을 재현할 수 없습니다. "3월 정산 당시 시스템은 어떤 요율을 알고 있었나?"에 답할 수 없습니다.

**방법.** 두 개의 시간 축을 둡니다.

- **유효 시간(valid time)** `valid_from`, `valid_to`: 현실에서 그 값이 적용되는 기간
- **기록 시간(transaction time)** `recorded_at`, `superseded_at`: 시스템이 그 사실을 알고 있던 기간

정정은 기존 행을 고치지 않고, **기존 행을 "대체됨"으로 닫고 새 행을 INSERT** 합니다(한 트랜잭션).

```python
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column


class FeeRate(Base):
    __tablename__ = "fee_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(6, 4))

    # 유효 시간: [valid_from, valid_to), valid_to=NULL 이면 무기한
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 기록 시간: 시스템이 이 행을 "사실"로 알고 있던 기간
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

```python
from sqlalchemy import and_, or_, select


def rate_as_of(merchant_id: int, valid_at: datetime, known_at: datetime):
    """valid_at 시점에 적용되는 요율을, known_at 시점에 시스템이 알던 대로 조회."""
    return select(FeeRate).where(
        FeeRate.merchant_id == merchant_id,
        FeeRate.valid_from <= valid_at,
        or_(FeeRate.valid_to.is_(None), FeeRate.valid_to > valid_at),
        FeeRate.recorded_at <= known_at,
        or_(FeeRate.superseded_at.is_(None), FeeRate.superseded_at > known_at),
    )
```

- 현재 기준 조회는 `valid_at=known_at=now()`, 감사(audit) 재현은 `known_at`을 과거로 둡니다.
- PostgreSQL에서는 "현재 유효한 행끼리 기간이 겹치지 않음"을 6번의 `EXCLUDE` 제약(`WHERE superseded_at IS NULL`)으로 DB가 보장하게 할 수 있습니다.
- 정말 이력이 필요한 도메인에만 적용하세요. 모든 테이블에 넣으면 쿼리 복잡도만 늘어납니다.

---

## 3. 금액은 `Decimal`, 환율은 이벤트 시점 스냅샷

### ✅ 적용됨: 금액 타입

`float`는 `0.1 + 0.2 == 0.30000000000000004`인 이진 부동소수점입니다. 이 보일러플레이트의 `Item.price`는 다음과 같이 바뀌었습니다.

| 계층 | 타입 | 위치 |
|---|---|---|
| DB | `NUMERIC(12, 2)` | `app/models/item.py` |
| Pydantic | `Decimal`, `max_digits=12`, `decimal_places=2`, `ge=0` | `app/schemas/item.py` |
| JSON | **문자열** `"10.50"` | Pydantic v2 기본 직렬화 |
| 집계 | `Decimal` 연산 + `quantize(0.01, ROUND_HALF_UP)` | `app/api/stats.py` |

- 소수점 셋째 자리(`"1.005"`)는 조용히 반올림하지 않고 **422**로 거부합니다.
- JSON에서 문자열로 주고받는 것은 의도된 동작입니다. JS의 `Number`도 부동소수점이라, 숫자로 보내면 클라이언트에서 정밀도가 깨질 수 있습니다. 플레이그라운드도 가격을 문자열로 보냅니다.
- 테스트: `test_price_is_exact_decimal`, `test_price_rejects_sub_cent_values`, `test_item_stats_money_is_exact`(0.10 + 0.20 = 정확히 0.30).

> ⚠️ **SQLite에는 정확한 십진수 타입이 없습니다.** SQLAlchemy가 읽을 때 `Decimal`로 바꿔 주지만 저장은 근사값입니다. 실제 돈을 다루는 운영 환경에서는 PostgreSQL(`NUMERIC`)을 쓰세요.

### 📘 가이드: 환율·금액은 이벤트 시점에 고정

**문제.** 결제 금액을 기준 통화로 보여 줄 때 리포트 쿼리에서 환율 테이블을 실시간으로 JOIN 하면, 환율이 바뀌는 순간 **과거 매출이 바뀝니다.**

**방법.** 결제를 만드는 시점에 사용한 환율과 환산 결과를 결제 행에 **함께 저장(스냅샷)** 합니다. 이후 리포트는 저장된 값만 읽습니다.

```python
class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payments_amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))       # 결제 통화 금액
    currency: Mapped[str] = mapped_column(String(3))               # ISO 4217, 예: USD

    # ↓ 결제 시점 스냅샷: 나중에 절대 다시 계산하지 않는다
    fx_rate: Mapped[Decimal] = mapped_column(Numeric(18, 8))       # 1 currency = fx_rate KRW
    fx_rate_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fx_rate_source: Mapped[str] = mapped_column(String(50))
    base_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))   # 기준 통화(KRW) 금액
```

```python
@router.post("/payments", status_code=201)
async def create_payment(data: PaymentCreate, session: AsyncSession = Depends(get_async_session)):
    quote = await fx_client.get_rate(data.currency, "KRW")   # 한 번만 조회
    payment = Payment(
        amount=data.amount,
        currency=data.currency,
        fx_rate=quote.rate,
        fx_rate_at=quote.timestamp,
        fx_rate_source=quote.source,
        base_amount=(data.amount * quote.rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP),
    )
    session.add(payment)
    await session.commit()
    return payment
```

- 반올림 규칙(자리수, `ROUND_HALF_UP`/`ROUND_HALF_EVEN`)은 회계/PG 정책에 맞춰 **한 곳**에서 정의하세요.
- 환율 원본 테이블은 2번(비템포럴)으로 관리하면 "그때 어떤 환율을 썼나"를 검증할 수 있습니다.

---

## 4. 미래 일정은 벽시계 시간(Wall Clock) + 타임존 이름

**문제.** "매일 아침 6시 알림", "다음 달 15일 09:00 근무"를 UTC 시각(`TIMESTAMPTZ`)으로 환산해서 저장하면, 그 사이 **서머타임(DST)이나 국가의 타임존 정책이 바뀔 때** 사용자가 의도한 "현지 6시"가 아니라 엉뚱한 시각에 실행됩니다.

**방법.** 미래 일정은 사용자의 의도 그대로 **날짜 + 현지 시각 + IANA 타임존 이름**으로 저장하고, 실행 직전에 UTC로 변환합니다.

```python
from datetime import date, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, field_validator
from sqlalchemy import Date, String, Time


class Shift(Base):
    __tablename__ = "driver_shifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    local_date: Mapped[date] = mapped_column(Date)
    local_start: Mapped[time] = mapped_column(Time)          # tz 없는 벽시계 시간
    time_zone: Mapped[str] = mapped_column(String(64))       # 예: "America/Toronto"


class ShiftCreate(BaseModel):
    local_date: date
    local_start: time
    time_zone: str

    @field_validator("time_zone")
    @classmethod
    def valid_iana_zone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("time_zone must be an IANA name, e.g. 'Asia/Seoul'")
        return v


def shift_start_utc(shift: Shift) -> datetime:
    """실행 시점에 최신 tz 규칙으로 UTC 시각을 계산."""
    local = datetime.combine(shift.local_date, shift.local_start, tzinfo=ZoneInfo(shift.time_zone))
    return local.astimezone(timezone.utc)
```

- **이미 일어난 일**(결제 시각, 로그인 시각, `created_at`)은 지금처럼 UTC `TIMESTAMPTZ`가 맞습니다. 이 규칙은 **미래**의 현지 시각 약속에만 해당합니다.
- DST 경계에는 존재하지 않는 시각(봄, 02:30)과 두 번 오는 시각(가을, 01:30)이 있습니다. `datetime.fold`로 어느 쪽인지 정하는 정책을 정해 두세요.
- `+09:00` 같은 오프셋이 아니라 `Asia/Seoul` 같은 **이름**을 저장해야 정책 변경을 따라갑니다. 서버 OS의 `tzdata`도 최신으로 유지하세요.

---

## 5. 소프트 딜리트와 조건부 유니크 인덱스

**문제.** `deleted_at`으로 소프트 딜리트를 하면서 `email`에 일반 `UNIQUE`를 걸면, 탈퇴한 사용자가 같은 이메일로 **재가입할 수 없습니다.** 그렇다고 앱에서 `if existing and not existing.deleted_at:`으로 우회하면 동시 요청에 뚫립니다(6번 참고).

**방법.** "삭제되지 않은 행끼리만 유니크"를 **조건부(partial) 유니크 인덱스**로 DB에 겁니다.

```python
from sqlalchemy import Index, text


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index(
            "uq_customers_email_active",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320))   # 컬럼 자체에는 unique=True 를 두지 않는다
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

- 소프트 딜리트를 쓰면 **모든 조회**에 `deleted_at IS NULL` 필터가 필요합니다. 누락을 막으려면 SQLAlchemy의 `with_loader_criteria`로 세션 단위 기본 필터를 거세요.
- **이 보일러플레이트의 사용자 테이블에는 해당하지 않습니다.** FastAPI Users는 실제로 행을 삭제하고(hard delete), `email`에 일반 unique 인덱스를 둡니다. 사용자 소프트 딜리트가 필요하면 `UserManager.delete`를 재정의하고 인덱스를 위처럼 바꿔야 합니다.
- 기존 테이블의 인덱스·제약 변경은 `create_all`로 반영되지 않습니다. **Alembic 마이그레이션**으로 관리하세요(`op.create_index(..., postgresql_where=...)`).

---

## 6. 비즈니스 규칙은 DB 제약으로 — 위반은 409 Conflict

**문제.** 서비스 계층에서 확인 후 쓰기를 하면,

```python
if await session.scalar(select(Booking).where(overlaps(...))):   # ① 확인
    raise HTTPException(409)
session.add(Booking(...))                                          # ② 쓰기
```

`async` 환경에서는 ①과 ② 사이의 `await`에서 다른 요청이 끼어듭니다. 동시에 들어온 두 요청이 모두 ①을 통과하고 둘 다 ②를 실행합니다(TOCTOU 경쟁 조건). 이런 Python 확인은 **UX용 빠른 실패**일 뿐 보장이 아닙니다.

### ✅ 적용됨

| 구성 | 위치 | 역할 |
|---|---|---|
| `uq_items_name` (UNIQUE) | `app/models/item.py` | 동시 요청에도 같은 이름은 하나만 |
| `ck_items_price_non_negative` (CHECK) | `app/models/item.py` | API 스키마를 우회한 쓰기(스크립트, 관리 도구)도 차단 |
| `IntegrityError → 409` 전역 핸들러 | `app/core/errors.py` | 모든 엔드포인트에서 동일한 응답, SQL/제약 이름 노출 없음 |
| `CRUDRouter` | `app/core/crud.py` | CrudRouter가 자체적으로 422(update 시에는 DB 에러 원문)로 바꾸던 것을 409로 통일 |

```bash
$ curl -X POST /api/items -d '{"name":"Keyboard","price":"49.90"}'   # 두 번째 요청
HTTP/1.1 409 Conflict
{"detail": "The request conflicts with existing data."}
```

테스트: `test_duplicate_name_conflict`, `test_update_to_duplicate_name_conflict`(실패한 수정이 롤백되는지 포함), `test_db_check_constraint`.

### 📘 가이드: 겹치는 예약 막기 (PostgreSQL `EXCLUDE`)

"같은 방에 시간이 겹치는 예약 금지"처럼 UNIQUE로 표현할 수 없는 규칙은 PostgreSQL의 배제(exclusion) 제약으로 겁니다.

```python
from sqlalchemy.dialects.postgresql import TSTZRANGE, ExcludeConstraint


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        ExcludeConstraint(
            ("room_id", "="),
            ("during", "&&"),            # && : 범위가 겹친다
            name="ex_bookings_no_overlap",
            using="gist",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    during = mapped_column(TSTZRANGE, nullable=False)   # 예: '[2026-01-01 09:00, 2026-01-01 10:00)'
```

```sql
-- 마이그레이션에서 한 번: '=' 연산자를 gist 인덱스에서 쓰기 위해 필요
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

- 겹치는 예약은 SQLSTATE `23P01`(exclusion violation)로 실패하고, SQLAlchemy가 이를 `IntegrityError`로 감싸므로 **위의 전역 핸들러가 그대로 409로 응답합니다.** 추가 코드가 필요 없습니다.
- 클라이언트에 어떤 규칙을 위반했는지 알려 줘야 한다면, 핸들러에서 `exc.orig`의 제약 이름(예: `ex_bookings_no_overlap`)을 사용자용 메시지에 매핑하세요. DB 에러 원문을 그대로 내보내지는 마세요.

---

## 체크리스트

새 도메인 모델을 추가할 때 확인하세요.

- [ ] `NULL`이 두 가지 이상의 의미를 가지지 않는가? → 상태 Enum + CHECK
- [ ] 값이 바뀌어도 과거 결과를 재현해야 하는가? → 비템포럴(INSERT, 덮어쓰기 금지)
- [ ] 돈인가? → `NUMERIC` / `Decimal`, JSON은 문자열
- [ ] 외부 변동값(환율, 가격표)으로 계산하는가? → 이벤트 시점 스냅샷 저장
- [ ] 미래의 현지 시각 약속인가? → 날짜 + 시각 + IANA 타임존 이름
- [ ] 소프트 딜리트인가? → 조건부 유니크 인덱스 + 조회 기본 필터
- [ ] "중복/겹침 금지" 규칙이 있는가? → UNIQUE / CHECK / EXCLUDE 제약 (Python 확인만으로는 부족)
- [ ] 스키마 변경을 Alembic 마이그레이션으로 관리하는가?
