# Báo cáo: Movie Discovery Agent

## Phân Tích Vấn Đề

Người dùng đã có lịch sử MovieLens và muốn khám phá phim bằng ngôn ngữ tự nhiên.
Một đề xuất tốt phải đồng thời: hợp ý định hiện tại, phản ánh sở thích dài hạn,
không vi phạm ràng buộc, chưa được người dùng chấm, và có lý do truy ngược được về
dữ liệu. Vì vậy đây không chỉ là bài toán search.

Ba khó khăn chính là: 51% phim có dưới 5 rating; tag rất thưa; plot dài nhưng truy
vấn ngắn. Ngoài ra hệ thống phải kết hợp tín hiệu content và collaborative, nhớ đề
xuất trước cho câu hỏi follow-up, và tránh để LLM bịa số liệu.

## Phương Pháp Tiếp Cận

Hệ thống gồm Streamlit UI độc lập và FastAPI backend. Lõi `MovieAgent` được xây dựng
` hỗ trợ tool calling với năm công cụ nghiệp vụ:
`recommend_movies`, `search_movies`, `get_user_profile`, `get_peer_opinion`, `find_blind_spots`.
LLM tự động phân tích ngữ cảnh để quyết định gọi tool phù hợp hoặc trả lời trực tiếp
(chào hỏi/small talk) mà không tạo kết quả rác. Lịch sử hội thoại được duy trì bằng
`InMemorySaver` checkpointer theo `thread_id` để phục vụ các câu hỏi follow-up.

Pipeline recommendation kết hợp:

- TF-IDF word unigram/bigram trên title, genre, tag và plot, có metadata boost.
- Content profile từ các phim người dùng đã chấm, mean-centered theo user.
- User-user collaborative filtering, cosine similarity, minimum overlap và
  shrinkage để giảm độ tin cậy của hàng xóm ít dữ liệu.
- Bayesian movie quality để các phim ít rating không chiếm top chỉ vì mean cao.
- Hard filters cho phim đã xem, genre loại trừ và khoảng năm.

Các object nặng được tạo một lần trong FastAPI lifespan. Với 5.135 phim tĩnh, index
in-memory đơn giản hơn và đủ nhanh; chưa cần một RAG microservice hay vector DB riêng.

### Nhật Ký Quyết Định


| Quyết định                     | Phương án thay thế đã xem xét           | Tại sao tôi chọn phương án này                                                       |
| ----------------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| Một LangChain tool-calling agent | Supervisor/multi-agent graph                   | Một model đủ chọn năm tool; cấu trúc ngắn, ít latency và dễ mở rộng provider   |
| TF-IDF local trong backend        | Tái sử dụng`rag_service` với Qdrant/Chroma | Corpus nhỏ, static; tránh thêm service và vận hành nhưng vẫn tìm tốt keyword/plot |
| Hybrid content + CF + quality     | Chỉ content, chỉ CF hoặc popularity         | Mỗi tín hiệu bù điểm yếu của tín hiệu khác và cho evidence dễ hiểu            |

## Đánh Giá

Hệ thống được đánh giá bằng 23 automated test và các hội thoại mẫu gần với yêu cầu
đề bài. Toàn bộ test hiện đều pass. Các tình huống chính gồm:

| Tình huống kiểm tra | Kết quả cần đạt | Kết quả |
|---|---|---|
| Đề xuất phim chung cho một user | Dùng lịch sử rating để đề xuất phim chưa xem | Đạt |
| Tìm “dark psychological thriller with a twist” | Trả về phim trong catalog có nội dung phù hợp | Đạt |
| Hỏi tiếp “Why would I like that?” | Giữ được ngữ cảnh của lượt đề xuất trước | Đạt |
| Hỏi đánh giá từ người có gu tương tự | Dùng rating của các user tương đồng và trả evidence | Đạt |
| Thích Toy Story nhưng không muốn Animation | Dùng phim tham chiếu nhưng loại đúng genre bị cấm | Đạt |
| Yêu cầu Action sau năm 2002 | Chỉ trả phim Action từ năm 2003 trở đi | Đạt |
| Yêu cầu đúng số lượng phim | Không trả nhiều hơn số lượng người dùng yêu cầu | Đạt |
| Tìm genre người dùng ít khám phá | Trả về blind spots cùng phim gợi ý chưa xem | Đạt |
| Chào hỏi thông thường | Trả lời trực tiếp, không gọi recommendation tool | Đạt |
| Kiểm tra grounding | Movie ID và evidence trả về đều thuộc dataset | Đạt |
| User không tồn tại | API từ chối request thay vì tạo recommendation sai | Đạt |

Ngoài test tự động, các hội thoại mẫu tại `evaluation/sample_conversations.md` được
dùng để kiểm tra cách trình bày câu trả lời, evidence và khả năng xử lý follow-up.

### Phân Tích Thất Bại

1. Với “dark psychological thriller with a twist”, `Zero Dark Thirty` có thể lọt
   top do chữ *dark* trong title và genre Thriller dù không phải psychological
   twist. TF-IDF hiểu khớp từ, không hiểu vai trò ngữ nghĩa. Embedding hoặc một
   reranker nhỏ trên top candidates sẽ khắc phục tốt hơn.
2. Với “liked Toy Story but tired of animated movies”, `A Kid in King Arthur's Court` khớp bốn genre nhưng CF chỉ 2.91/5. Query relevance đang có thể lấn át
   tín hiệu dislike. Có thể thêm ngưỡng predicted rating hoặc học weights trên
   validation set.
3. “Blind spot” hiện đo under-exposure tương đối so với catalog, chưa phân biệt
   user cố ý tránh một genre với việc chưa khám phá nó. Cần hỏi lại người dùng hoặc
   dùng cả rating sentiment trước khi gọi đó là điểm mù.

## Suy Ngẫm

Điểm mạnh là toàn bộ số liệu đều đến từ dataset, chạy offline mặc định, cấu trúc
service rõ và demo được end-to-end. Hard constraints được áp dụng trước ranking nên
không thể bị LLM bỏ qua. UI chỉ gọi HTTP, do đó backend có thể tái sử dụng bởi client
khác.

Điểm yếu là TF-IDF thuần chưa nắm tốt các sắc thái ngữ nghĩa tinh tế (như trường hợp
từ khóa trùng lặp nhưng khác ngữ cảnh); evaluation 100 user và một held-out item/user
có variance cao.
Nếu có thêm thời gian, tôi sẽ đánh giá nhiều temporal folds, đo constraint success
và explanation faithfulness, bổ sung semantic reranking, rồi mới cân nhắc tách
retrieval thành microservice khi corpus hoặc tải vận hành thực sự yêu cầu.

## Phần Mở

Thiết kế cố ý đặt LLM sau retrieval/ranking. Vì vậy bật OpenAI/Gemini có thể làm câu
trả lời tự nhiên hơn nhưng không thay đổi danh sách phim, số rating hay confidence.
Điều này giữ demo có thể tái tạo mà không cần API key và giảm rủi ro hallucination.
