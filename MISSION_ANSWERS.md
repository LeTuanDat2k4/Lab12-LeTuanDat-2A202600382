# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. **API Key bị hardcode**: Việc lưu API key trực tiếp trong mã nguồn gây rủi ro bảo mật lớn nếu đẩy code lên public repository (như GitHub).
2. **Hardcode Port**: Port cố định ở `8000` làm mất tính linh hoạt, trong khi cloud provider thường cung cấp Port động thông qua biến môi trường `$PORT`.
3. **Debug Mode bật trên production (`debug=True`)**: Rủi ro tiết lộ thông tin nhạy cảm qua các thông báo lỗi hoặc stack trace.
4. **Không có Health Check**: Hệ thống nền tảng (Platform) sẽ không biết ứng dụng còn đang chạy tốt hay không để tự động restart khi có lỗi.
5. **Không có Graceful Shutdown**: Khi tắt app, ứng dụng sẽ tắt đột ngột và cắt ngang các request đang xử lý dang dở.

### Exercise 1.3: Comparison table
| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| Config | Hardcode trong code | Đọc từ env vars | Giúp dễ cấu hình tuỳ môi trường mà không cần sửa code, không lộ secrets ra source control. |
| Health check | Không có | Có (`GET /health`) | Giúp Load balancer và Orchestrator (K8s, Render) biết khi nào app lỗi để tự khởi động lại. |
| Logging | `print()` | Structured JSON | Dễ dàng cho máy học, hệ thống (như Datadog, ELK) parse, search và phân tích log. |
| Shutdown | Tắt đột ngột | Graceful Shutdown | Tránh mất dữ liệu, hoàn thành xong các request đang dở trước khi tắt hẳn ứng dụng. |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. **Base image:** `python:3.11-slim` (Là image Python 3.11 đã được thu gọn, giúp giảm dung lượng image).
2. **Working directory:** `/app` (Nơi chứa mã nguồn chính của ứng dụng trong container).
3. **Tại sao COPY requirements.txt trước?** Để tận dụng cơ chế Docker Cache Layer. Nếu requirements không đổi, Docker không cần cài lại package, giúp tăng tốc quá trình build.
4. **CMD vs ENTRYPOINT:** `CMD` cung cấp lệnh thực thi mặc định và dễ dàng bị ghi đè (override) khi chạy container. `ENTRYPOINT` định nghĩa file/lệnh chính mà container luôn chạy và khó bị ghi đè hơn.

### Exercise 2.3: Image size comparison
- Develop: ~1.2 GB (python:3.11 base image chuẩn)
- Production: ~150-300 MB (dùng alpine/slim và multi-stage)
- Difference: ~80% nhỏ hơn nhờ vứt bỏ các build dependencies (gcc, header files) không cần thiết ở runtime.

## Part 3: Cloud Deployment

### Exercise 3.1: VPS deployment
- URL: http://103.72.99.109:7777/
- Screenshot: [Link to screenshot in repo](./06-lab-complete/test.png)

## Part 4: API Security

### Exercise 4.1-4.3: Test results
```bash
# 4.1: Test API Key
$ curl -X POST http://localhost:8000/ask -d '{"user_id":"test","question":"Hi"}'
{"detail":"Invalid or missing API key. Include header: X-API-Key: <key>"}

$ curl -H "X-API-Key: dev-key-change-me" -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"user_id":"test","question":"Hi"}'
{"question":"Hi","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","history":[],"model":"gpt-4o-mini","timestamp":"..."}

# 4.3: Rate Limiting
# Gửi 21 request trong 1 phút, request 21 sẽ bị lỗi:
{"detail":"Rate limit exceeded: 20 req/min"}
```

### Exercise 4.4: Cost guard implementation
**Cách thực hiện (Cost Guard bằng Redis):**
Mỗi khi người dùng gọi API, chúng ta sẽ tính `input_tokens` và `output_tokens` và quy đổi ra chi phí (USD). Sau đó, dùng khóa `cost:YYYY-MM-DD` trên Redis để đếm cộng dồn chi phí (`INCRBYFLOAT`). Trước khi xử lý, nếu giá trị đã lưu > budget cho phép ($10) thì API sẽ trả về lỗi `503 Daily budget exhausted`, bảo vệ chúng ta không bị vượt quá ngân sách API. Redis cũng được thiết lập `EXPIRE` để tự xoá ngày cũ.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
1. **Health/Readiness Check:** Viết thêm 2 endpoint `/health` (liveness) và `/ready` (kiểm tra connection Redis). Việc này giúp hệ thống (như Kubernetes hoặc Railway) chỉ định hướng traffic vào agent khi agent đã kết nối DB thành công.
2. **Graceful shutdown:** Bắt tín hiệu `SIGTERM` bằng module `signal`. Khi nhận tín hiệu, ứng dụng sẽ không nhận request mới, xử lý xong request hiện tại rồi mới `sys.exit(0)`. (Thực tế Uvicorn đã tự làm việc này qua flag `timeout_graceful_shutdown`).
3. **Stateless Design:** Đây là bước cực kỳ quan trọng. Chúng ta đã đưa logic lưu "Conversation History" từ bộ nhớ dictionary `conversation_history = {}` sang lưu trong Redis `r.lrange(key)` và `r.rpush(key)`. Vì thế khi chạy 3 agent bằng `docker-compose up --scale agent=3`, người dùng gửi request vào agent nào cũng sẽ có lại đoạn chat cũ.
