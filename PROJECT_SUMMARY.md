# FastAPI Boilerplate V3 - Project Summary

## 🎉 프로젝트 생성 완료!

V2 템플릿(UV + Jinja2 + `run.sh`) 구조를 그대로 유지하면서, 실무 API에 거의 항상 필요한 4가지 확장을 통합한 보일러플레이트입니다.

| 라이브러리 | 역할 | 한 줄 요약 |
|---|---|---|
| FastAPI Users | 로그인/회원관리 | "보안과 인증 고민 끝" |
| FastAPI-CrudRouter | CRUD 자동 생성 | "코딩 시간을 줄여주는 마법" |
| FastAPI-Limiter | 트래픽 제한 | "서버 마비를 막는 방패" |
| FastAPI-Cache | 응답 캐싱 | "서버 성능 10배 끌어올리기" |

### 🚀 빠른 시작

```bash
cp .env.example .env     # SECRET_KEY 변경
./run.sh                 # 의존성 설치 + 서버 실행
./run.sh createsuperuser admin@example.com 'password'
```

- 플레이그라운드: http://localhost:8000/ (회원가입 → 로그인 → CRUD → 리밋 → 캐시를 버튼으로 체험)
- Swagger UI: http://localhost:8000/docs

### ✅ 구현된 기능들

#### 🔐 FastAPI Users (`app/core/users.py`, `app/api/auth.py`)
- 회원가입, JWT 로그인/로그아웃, 비밀번호 재설정, 이메일 인증, `/users/me`
- `current_active_user`, `current_superuser` 의존성으로 엔드포인트 보호
- `UserManager` 훅(`on_after_register` 등)에서 메일 발송 연동 가능
- 인증 엔드포인트에 별도 레이트 리밋(기본 10회/60초) → 무차별 대입 방어

#### ✨ FastAPI-CrudRouter (`app/api/items.py`)
- `SQLAlchemyCRUDRouter` 선언 하나로 Item 목록/조회/생성/수정/삭제/전체삭제 생성
- 읽기는 공개, 쓰기는 로그인, 전체삭제는 슈퍼유저만
- 쓰기 시 `items` 캐시 네임스페이스 자동 무효화

#### 🛡 FastAPI-Limiter (`app/core/limiter.py`)
- `rate_limit(times, seconds)` 의존성 팩토리
- 클라이언트(IP + 경로)별 독립 버킷, 초과 시 `429 Too Many Requests`
- 기본 인메모리, `REDIS_URL` 설정 시 Redis 공유 버킷

#### ⚡ FastAPI-Cache (`app/core/cache.py`, `app/api/stats.py`)
- `@cache(expire=..., namespace=...)` 데코레이터, `X-FastAPI-Cache: HIT/MISS` 헤더
- 요청(method + path + query) 기반 캐시 키 → DB 세션 의존성이 있어도 정상 캐싱
- 기본 인메모리, `REDIS_URL` 설정 시 Redis 백엔드

#### 🧱 데이터 무결성 (`docs/design-guide.md`)
- 금액은 `NUMERIC(12,2)` / `Decimal` (JSON은 문자열, 소수 셋째 자리는 422)
- 비즈니스 규칙은 DB 제약으로: `uq_items_name`(UNIQUE), `ck_items_price_non_negative`(CHECK)
- `IntegrityError` → `409 Conflict` 전역 핸들러 (SQL/제약 이름 노출 없음)
- NULL 의미 분리, 비템포럴 이력, 환율 스냅샷, 벽시계 시간, 소프트 딜리트는 설계 가이드로 정리

#### ➕ 추가 구성
- SQLAlchemy 2.0 (FastAPI Users용 async 엔진 + CrudRouter용 sync 엔진, 동일 DB)
- GZip 응답 압축
- 슈퍼유저 생성 스크립트 (`./run.sh createsuperuser`)

### 🧪 테스트 커버리지

`./run.sh test` — 35개 테스트

- `test_health.py`, `test_main.py`: 헬스체크, 페이지, 문서, OpenAPI
- `test_auth.py`: 가입/중복/권한상승 차단/로그인 실패/토큰/보호 엔드포인트
- `test_items.py`: CRUD 흐름, 검증, 페이지네이션, 권한(로그인/슈퍼유저), Decimal 금액, 중복 이름 409(생성·수정), DB CHECK 제약
- `test_limiter.py`: 429 발생, 클라이언트별 독립 제한
- `test_cache.py`: 캐시 HIT, 쓰기 후 무효화, HIT/MISS 응답 동일성, 금액 합계 정확성(0.10 + 0.20 = 0.30), 캐시 삭제 권한

`./test_quick.sh` — 실제 서버를 띄워 모든 기능을 curl로 스모크 테스트

### 🔧 호환성 메모

- **fastapi-crudrouter 0.8.6**은 Pydantic v1 기준이라 `app/core/crudrouter_compat.py`에서 v2용으로 패치합니다.
- **fastapi-limiter 0.2.0**은 최신 FastAPI에서 `app.routes` 스캔 중 오류가 나고, 모든 클라이언트가 버킷 하나를 공유합니다. `app/core/limiter.py`에서 둘 다 보완했습니다.

### 📚 다음 단계

- Alembic 마이그레이션 도입 (현재는 시작 시 `create_all`)
- `UserManager` 훅에 실제 이메일 발송 연결
- 운영 환경에서 `REDIS_URL` + PostgreSQL 설정
- OAuth 로그인(FastAPI Users의 `get_oauth_router`) 추가
