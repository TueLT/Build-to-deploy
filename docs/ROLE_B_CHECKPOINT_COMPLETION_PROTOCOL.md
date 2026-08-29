# Product Delivery Agent — Checkpoint Completion Protocol

> Áp dụng cho mọi checkpoint của ROLE_B. Một checkpoint **không được coi là hoàn thành** chỉ vì code đã viết hoặc demo fixture chạy được.

## 1. Trình tự bắt buộc

```text
Implement scoped work
  -> Run required tests/checks
  -> Có lỗi?
       -> Có: phân loại -> sửa đúng nguyên nhân -> chạy lại toàn bộ checks liên quan
       -> Không: viết checkpoint report chi tiết
  -> Final verification
  -> Mark checkpoint complete
```

Không được đảo thứ tự bằng cách viết báo cáo “đã xong” rồi mới kiểm thử.

## 2. Definition of Done cho một checkpoint

Chỉ đánh dấu `complete` khi tất cả điều kiện đúng:

- Code/fixture/documentation thuộc scope checkpoint đã được hoàn thiện.
- Unit test mới cho behavior thay đổi đã có.
- Regression test liên quan đã chạy xanh.
- Ruff và `git diff --check` xanh.
- Dataset/contract check liên quan đã chạy xanh.
- Không còn bug P0/P1 đã biết trong scope checkpoint.
- Các shared-platform dependency chưa có được ghi rõ là `blocked`, không bị fake/mock như production.
- Có review đối chiếu checkpoint với ROLE_B plan theo mục 4A trước khi dùng trạng thái `complete`.
- Có checkpoint report theo format ở mục 5.

## 3. Khi kiểm thử phát hiện bug

Mỗi failure phải được xử lý theo vòng lặp sau:

1. **Reproduce**: giữ lại command, test case và input tối thiểu gây lỗi.
2. **Classify**: gắn một nguyên nhân chính: `domain_rule`, `authorization`, `consent`, `source_provenance`, `tool`, `schema`, `runtime`, `UI`, `test_fixture` hoặc `infrastructure`.
3. **Fix root cause**: không sửa expected fixture hay nới policy chỉ để test xanh.
4. **Add regression test**: test phải fail trước fix và pass sau fix.
5. **Re-run**: chạy test mới, test module liên quan, security/dataset checks liên quan.
6. **Record**: nếu bug ảnh hưởng nghiệp vụ/security, ghi root cause và evidence trong checkpoint report.

Nếu failure là dependency ngoài scope của B, không được tạo bypass. Ghi rõ owner/gate/blocker trong report và giữ feature flag tắt.

## 4. Kiểm thử tối thiểu

Chọn đúng module theo checkpoint; không cần chạy các lệnh không liên quan chỉ để tạo số lượng test.

```powershell
# Delivery domain/schema/profile
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_product_delivery.py -q

# Scope và Delivery tools
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py -q

# Brief producer/handoff
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_delivery_brief.py -q

# Shared dataset contract
.\.venv\Scripts\python.exe -m pytest tests\test_multi_agent_dataset.py -q
.\.venv\Scripts\python.exe scripts\generate_multi_agent_dataset.py --check
.\.venv\Scripts\python.exe scripts\validate_multi_agent_dataset.py

# Static/change integrity
.\.venv\Scripts\python.exe -m ruff check src tests scripts
git diff --check
```

Khi đã có DB/runtime/UI thật, checkpoint tương ứng phải bổ sung migration, integration, authorization/revoke, E2E và production build checks vào danh sách bắt buộc.

## 4A. Plan-alignment review bắt buộc

Sau khi test xanh nhưng **trước khi viết trạng thái cuối của report**, owner checkpoint phải đối chiếu
artifact với [ROLE_B Product Delivery plan](ROLE_B_PRODUCT_DELIVERY_AGENT_7_DAY_PLAN.md).

Review phải trả lời, bằng bảng ngắn:

| Hạng mục cần kiểm | Yêu cầu |
|---|---|
| Plan task/capability | Nêu đúng ID như `B2-03`, `B3-04`, `DLV-C08` hoặc gate A-DLV liên quan |
| Trạng thái thực | Chỉ dùng `complete`, `partial`, `blocked` hoặc `not_started` |
| Evidence | File/artifact và test command chứng minh |
| Phạm vi còn thiếu | Nêu rõ implementation nào chưa có, không gộp vào completed scope |
| Gate | Dependency owner + A-DLV/feature flag nếu có |

Quy tắc diễn giải:

- Một checkpoint fixture/unit-test có thể là `complete / verified` **trong phạm vi checkpoint**, nhưng
  không được gọi là “PR-B2 complete”, “Day 2 complete” hoặc “Delivery Agent complete” nếu task
  integration/E2E tương ứng còn `partial`/`blocked`.
- `partial` không phải failure nếu phần còn lại đang chờ gate đã biết; report phải nêu gate đó.
- Không được nâng trạng thái nhờ mock/fallback/bypass quyền. Test fixture chỉ chứng minh contract
  và domain behavior, không chứng minh DB/runtime/UI production behavior.
- Nếu plan thay đổi scope/role/contract, cập nhật plan trước hoặc cùng checkpoint và nêu link tới
  quyết định; không âm thầm làm lệch plan.

## 5. Checkpoint report bắt buộc

Chỉ tạo `docs/ROLE_B_IMPLEMENTATION_CHECKPOINT_<NN>.md` sau khi mục 2 và 4 xanh. Report phải có:

1. Trạng thái checkpoint và phạm vi chính xác.
2. Artifact/file đã thêm hoặc sửa.
3. Hành vi/nghiệp vụ đã triển khai, bao gồm source/scope/consent behavior nếu có.
4. Test command, kết quả và số test pass.
5. Bug đã phát hiện/fix trong checkpoint; nếu không có, ghi rõ “không có failure trong bộ kiểm thử đã chạy”.
6. Known limits và shared gates chưa hoàn thành.
7. Bước tiếp theo, owner và điều kiện để integration/release.
8. Bảng **Plan-alignment review** theo mục 4A, kết luận rõ checkpoint đang hoàn thành task nào và
   task nào vẫn partial/blocked.

Không dùng các câu mơ hồ như “đã hoàn thành agent” khi mới hoàn tất schema, fixture, prompt hoặc adapter chưa được wire vào runtime.

## 6. Quy tắc báo cáo trạng thái

| Trạng thái | Khi nào dùng |
|---|---|
| `in_progress` | Đang implement hoặc đang xử lý test failure |
| `blocked` | Không thể tiến tới integration mà không có dependency/gate được nêu rõ |
| `verified` | Scope checkpoint đã qua bộ kiểm thử bắt buộc nhưng chưa được merge/release |
| `complete` | Đã `verified` và checkpoint report đã được ghi đủ evidence |

Feature flag chỉ được bật sau checkpoint integration/E2E tương ứng, không phải sau checkpoint fixture/unit test.
