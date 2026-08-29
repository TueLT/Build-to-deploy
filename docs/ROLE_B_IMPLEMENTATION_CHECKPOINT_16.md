# Workspace Agent Runtime Isolation — Checkpoint 16

> Trạng thái: **complete / verified trong local Docker integration scope cho R0–R2**. Checkpoint này không đồng nghĩa
> toàn bộ R0–R7 hoặc kiến trúc production đã hoàn tất. R3 Registry, R4 Personal service, R5 provisioning, R6 distributed
> bulkhead/queue và R7 production rollout vẫn còn ở phía sau.

## 1. Mục tiêu checkpoint

Chuyển Product Delivery Agent từ graph được gọi trực tiếp trong Core process sang một runtime service có fault boundary
thật, trong khi giữ nguyên public API/UI và giữ `embedded` adapter làm đường rollback.

Kết quả bắt buộc:

- Personal checkpointer lỗi không làm Core và deterministic Workspace API sập theo.
- Product Delivery runtime có contract nghiêm ngặt, chỉ nhận authorized snapshot do Core tạo.
- Runtime được khóa theo Agent Workspace, profile và version; target sai bị từ chối trước LLM.
- Core gọi runtime qua internal HTTP có ký HMAC; không chuyển user JWT hay database credential sang runtime.
- Dừng container Delivery không làm Core/Personal dừng; readiness chỉ degraded đúng component.
- Public Delivery endpoint vẫn trả brief đã xác thực dạng `partial` khi lớp AI không khả dụng.

## 2. Artifact đã triển khai

### Runtime boundary và bảo mật

- `src/agents/runtime/contracts.py`: request/response, target, actor, authorization, usage và runtime metadata; mọi contract
  dùng `extra=forbid` và immutable.
- `src/agents/runtime/security.py`: chữ ký HMAC-SHA256 gắn timestamp, constant-time comparison và cửa sổ chống replay.
- `src/agents/runtime/executor.py`: Product Delivery executor chỉ dựng dedicated Delivery graph từ snapshot đã cấp quyền.
- `src/agents/runtime/adapters.py`: embedded adapter, remote HTTP adapter, deadline và local bulkhead theo
  `agent_workspace_id`.
- `src/workspace_agent_runtime/main.py`: FastAPI service riêng với liveness, readiness và internal run endpoint.

### Core integration và fault boundary

- `src/api/delivery_routes.py`: giữ nguyên public route; Core vẫn làm authorization, scoped DB read và compact snapshot,
  sau đó mới gọi runtime adapter. Runtime failure không làm mất deterministic brief.
- `src/main.py`: component readiness; Personal checkpointer init được cô lập; scheduler cleanup của Personal chỉ đăng ký khi
  Personal sẵn sàng.
- `src/api/routes.py`, `src/api/assistant_routes.py`, `src/services/assistant_thread_service.py`: Personal unavailable trả
  `503` rõ ràng, không dereference graph/checkpointer rỗng.
- `src/services/component_health_service.py`: registry health theo component.
- `src/config.py`, `.env.example`: runtime mode, URL, secret, timeout, signature age, Workspace/profile/version pin và
  per-Workspace concurrency.

### Deployment

- `docker-compose.yml`: thêm container `workspace-agent-product-delivery`, port 8010, healthcheck, CPU/memory limit và
  Core chạy remote mode. Secret và demo Workspace ID có thể override bằng environment.
- Runtime không chạy migration, không có user JWT và không cần database credential để sinh câu trả lời từ snapshot.

### Regression/fault tests

- `tests/test_agents/test_runtime_isolation.py`: strict contract, snapshot tamper, HMAC/replay, target mismatch trước LLM,
  signed invocation, remote adapter và per-Workspace bulkhead.
- `tests/test_agents/test_delivery_api.py`: runtime outage vẫn trả Delivery facts hợp lệ dạng `partial` và data gap
  `DELIVERY_AGENT_RUNTIME_FAILED`.
- `tests/test_assistant_threads.py`: fixture lịch sử Personal được sửa để dùng request nghiệp vụ rõ ràng, phù hợp guardrail.

## 3. Luồng vận hành sau checkpoint

```text
Browser
  -> Core public Delivery API
  -> identity + membership + business-role policy
  -> scoped task/milestone/message/people reads
  -> compact authorized ToolResult snapshot + SHA-256 binding
  -> HMAC-signed internal request
  -> Product Delivery runtime container
  -> dedicated Delivery system prompt + guardrails + snapshot-only tool + Groq LLM
  -> strict AgentRuntimeResponse
  -> Core audit + token usage attribution + unchanged public ToolResult
```

Runtime không nhận quyền tự chọn Workspace/group và không tự query database. `agent_workspace_id`, profile, version,
snapshot hash và authorization expiry đều do Core gắn vào envelope và được runtime kiểm tra lại.

## 4. Fault behavior đã xác nhận

| Failure injection | Kết quả thực |
|---|---|
| Personal checkpointer init ném exception | Hàm init trả degraded; Core tiếp tục khởi động |
| Personal graph/checkpointer không tồn tại | `/api/v1/chat` trả `503`; không gây lỗi 500 do dereference |
| Delivery adapter mất kết nối | Public Delivery brief trả `200 partial`, facts/sources còn nguyên và thêm runtime data gap |
| Delivery container bị stop | Core `/health=ok`, Personal `/api/v1/status=ready`, Core readiness `degraded`, chỉ Delivery false |
| Delivery container restart | Runtime và Core readiness trở lại `ready` mà không restart Core |
| Signed target sai Workspace | Runtime thật trả `403 Runtime target mismatch`; executor/LLM không được gọi trong regression test |
| Workspace A hết local concurrency | Chỉ A nhận busy; Workspace B vẫn nhận slot và hoàn thành |

## 5. Kiểm thử và evidence

### Static và contract/runtime regression

```powershell
.\.venv\Scripts\python.exe -m ruff check <runtime/core/test files>
```

Kết quả: **passed**.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_agents -q
```

Kết quả: **117 passed, 1 skipped**.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Kết quả cuối: **431 passed, 1 skipped, 26 warnings** trong khoảng 6 phút 16 giây. Không còn failure.

`git diff --check`: **passed**; chỉ có cảnh báo LF/CRLF của Git trên Windows.

### Frontend production build

```powershell
cd Frontend\user
npm run build
```

Kết quả: **passed**, 717 modules transformed. Calendar chunk lớn hơn 500 kB vẫn là warning đã biết, không thuộc runtime
isolation.

### Docker và live smoke

```powershell
docker compose config --quiet
docker compose build workspace-agent-product-delivery backend
docker compose up -d postgres workspace-agent-product-delivery backend
```

Kết quả: Compose hợp lệ; hai image build thành công; Postgres, runtime và Core healthy.

Trước fault:

```json
{"Core":"ok","CoreReady":true,"Readiness":"ready","Personal":"ready","DeliveryRuntime":"ready"}
```

Sau khi stop riêng Delivery runtime:

```json
{"Core":"ok","CoreReady":true,"Readiness":"degraded","Personal":"ready","DeliveryReady":false}
```

Sau restart: Core readiness và Delivery component trở lại `ready`.

Live public API bằng tài khoản Lead demo đi qua Core -> remote container -> Groq:

```json
{"Status":"success","HasAgentResponse":true,"SourceCount":7,"DataGaps":""}
```

## 6. Bug/failure phát hiện và đã sửa

1. Mock `httpx.Response` thiếu request nên `raise_for_status()` lỗi. Phân loại `test_fixture`; sửa mock đúng contract HTTP.
2. WebSocket tests patch lifecycle hook cũ. Phân loại `runtime compatibility`; giữ alias `init_checkpointer` và
   `close_checkpointer` nhưng implementation vẫn đi qua fault boundary mới.
3. `test_submit_log.py` nạp `.env` khi pytest collection, làm test feature-flag mặc định vô tình kế thừa cờ demo và gọi
   Groq thật. Phân loại `test_fixture`; test nay truyền hai cờ false tường minh.
4. Test Assistant history dùng câu quá mơ hồ nên guardrail mới đúng nghiệp vụ trả clarification thay vì gọi fake LLM.
   Phân loại `test_fixture/domain_rule`; đổi fixture thành yêu cầu lập kế hoạch công việc rõ ràng, không nới guardrail.
5. Docker daemon ban đầu đang dừng. Phân loại `infrastructure`; khởi động Docker Desktop rồi build/fault gate thành công.

## 7. Known limits và gate tiếp theo

- R3 chưa có Registry/Gateway. Core hiện lookup runtime bằng config URL; Docker pin Product Delivery demo Workspace bằng
  environment. Chưa thể tự động route hàng trăm Workspace hoặc canary từng Workspace.
- R4 chưa tách Personal thành container. Checkpoint này chỉ đảm bảo lỗi khởi tạo Personal không kéo Core/Delivery xuống;
  crash toàn Core process vẫn ảnh hưởng Personal và public API.
- Bulkhead hiện là local in-process. Redis/distributed concurrency, token budget, queue, DLQ và circuit breaker thuộc R6.
- HMAC secret local cần chuyển sang secret manager và bổ sung mTLS/service identity trước staging production.
- Automated provisioning, scale-to-zero, version rollout ring và suspend/archive runtime thuộc R5.
- Delivery server-side thread/context, source deep-link/freshness, dashboard audit và browser E2E còn là P1 của functional
  plan; process extraction không tự hoàn thành các mục đó.
- Production load/soak/security/canary và rollback rehearsal thuộc R7; chưa được suy diễn từ local Docker pass.

## 8. Plan-alignment review

| Plan task/capability | Trạng thái | Evidence | Còn thiếu / gate |
|---|---|---|---|
| R0 runtime boundary | `complete` local | strict contracts, tamper/replay tests, full regression | Release tag/schema compatibility policy |
| R1 component fault boundary | `complete` local | health registry, Personal containment, timeout, local bulkhead | Distributed counters thuộc R6 |
| R2 Delivery runtime extraction | `complete` local Docker | image/service, signed adapter, kill/restart, live Groq smoke | Staging canary + secret manager |
| R3 Registry/Gateway | `not_started` | Không có migration/registry lookup | Dependency trực tiếp tiếp theo |
| R4 Personal service | `not_started` | Personal vẫn trong Core | Chỉ bắt đầu sau R3 |
| R5 provisioning | `not_started` | Một demo service pin bằng env | Cần desired-state/provisioner |
| R6 distributed scale | `not_started` | Local bulkhead là bước chuẩn bị | Cần Redis/queue/load evidence |
| R7 production acceptance | `not_started` | Local gates xanh | Cần staging/soak/canary/runbook |

## 9. Kết luận

R0–R2 đã được triển khai và kiểm chứng trong local Docker integration scope: Product Delivery là runtime process riêng,
Core giữ authorization/data boundary, Personal lỗi không chặn startup, và Delivery container lỗi không kéo Personal/Core
đi theo. Kiến trúc hiện đã có fault boundary thật cho Product Delivery, nhưng chưa phải nền tảng multi-Workspace production
hoàn chỉnh cho đến khi R3–R7 được thực hiện theo đúng gate.
