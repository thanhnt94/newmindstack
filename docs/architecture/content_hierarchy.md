# Kiến Trúc Dữ Liệu Học Tập Đa Hình (Content Hierarchy)

Một trong những bài toán thiết kế cơ sở dữ liệu lớn nhất của hệ thống EdTech là việc có quá nhiều loại nội dung học tập (Khóa học, Flashcard Set, Bài giảng, Câu đố MCQ, Gõ chữ...). 
Nếu tạo mỗi bảng cho một loại (ví dụ: `courses`, `flashcard_sets`, `quizzes`...) hệ thống sẽ bị phình to (Database Bloat) và cực kỳ khó khăn khi viết tính năng dùng chung (ví dụ: Tính năng Đánh dấu Yêu thích, Thống kê học tập).

MindStack giải quyết vấn đề này bằng mô hình **Polymorphic Database (Đa Hình CSDL)** và kiến trúc Container-Item.

---

## 1. Hệ Thống Hai Cấp Cơ Bản (Two-Tier System)

Mọi nội dung trong MindStack đều tuân theo mô hình 2 cấp:
1. **Container (Tệp chứa)**: Cấp độ cao nhất. Dùng để gom nhóm, bao bì (Ví dụ: Khóa Học TOEIC, Bộ Thẻ Flashcard JLPT N5). 
2. **Item (Phần tử)**: Cấp độ chi tiết gắn liền với Container. Đây là thứ thực sự được "học" (Ví dụ: Bài giảng số 1, Thẻ từ vựng 'Apple', Câu hỏi trắc nghiệm A/B/C).

*(Giới thiệu Cấp Trung Gian: `learning_groups`. Một Container có thể chứa các Nhóm (VD: Chương 1, Unit 2) và Item thuộc về các Nhóm đó. Nếu không phức tạp, Item gắn trực tiếp vào Container).*

---

## 2. Lõi Thiết Kế SQLAlchemy (Single Table Inheritance)

Kiến trúc này dựa vào tính năng **Single Table Inheritance (Kế thừa Đơn bảng)** của SQLAlchemy:

### A. The Container Table (`learning_containers`)
- Chứa MỘT bảng duy nhất cho toàn bộ các gói học tập trên hệ thống.
- Cột `container_type` đóng vai trò là **Discriminator (Bộ phân loại)**. Các giá trị khả dụng: `COURSE`, `FLASHCARD_SET`, `QUIZ_SET`.
- Trong SQLAlchemy:
  ```python
  class BaseContainer(db.Model):
      __tablename__ = 'learning_containers'
      container_id = db.Column(db.Integer, primary_key=True)
      container_type = db.Column(db.String(50))
      title = db.Column(db.String(255))
      
      __mapper_args__ = {
          'polymorphic_on': container_type,
          'polymorphic_identity': 'BASE'
      }
      
  class Course(BaseContainer):
      __mapper_args__ = {'polymorphic_identity': 'COURSE'}
      
  class FlashcardSet(BaseContainer):
      __mapper_args__ = {'polymorphic_identity': 'FLASHCARD_SET'}
  ```

### B. The Item Table (`learning_items`)
- Hoạt động tương tự bảng Container.
- Cột `item_type` (Discriminator) quyết định nó là `FLASHCARD`, `LESSON`, hay `QUIZ_MCQ`.
- Cấu trúc nội dung chi tiết (Mặt trước thẻ từ, Các đáp án A B C, Nội dung Markdown bài giảng) đều được lưu trữ chung vào một cột có kiểu dữ liệu là **`JSON (content)`**. 
- Schema JSON này được phân tích (parse) bằng Pydantic Models hoặc Schemas riêng biệt tại tầng Logic của từng Module (ví dụ: Module `flashcard` sẽ parse JSON này thành `front` và `back`).

---

## 3. Lợi Ích Vượt Trội Của Kiến Trúc

1. **Khả Năng Tái Sử Dụng Rất Cao**:
   - Chức năng Tracking History (`study_logs`), FSRS (`item_memory_states`) hay Gamification chỉ cần ánh xạ (FK) tới một ID duy nhất là `item_id`. Nó hoàn toàn không cần quan tâm Item đó thuộc dạng gì.
   - Tính năng Đánh giá sao (Rating), Yêu thích (Favorite), hay Gắn Tags của Container được viết 1 lần duy nhất trên `BaseContainer` và áp dụng cho cả Khóa Học lẫn Bộ Thẻ.
2. **Khả Năng Mở Rộng Dễ Dàng (Future-Proof)**:
   - Nếu tương lai hệ thống muốn ra mắt 1 thể loại học tập mới (ví dụ: Video Interactive). Database không cần thay đổi `migrate` thêm bảng mới. Chỉ cần tạo một class SQLAlchemy mới kế thừa từ `learning_items` và đăng ký một `item_type = 'VIDEO'`.
3. **Hiệu Suất Tìm Kiếm**:
   - Tất cả dữ liệu tập trung ở 1-2 bảng chính hỗ trợ Full-Text Search qua cột `search_text` đồng nhất cho ElasticSearch hoặc Postgres TSVector.

---

### Mối Quan Hệ Giữa Module Code và Data
Vì `learning_containers` và `learning_items` phân bổ xuyên suốt hệ thống, chúng được đặt tại Module nền tảng là `mindstack_app/modules/learning/`.
- Khi module `vocab_flashcard` muốn cấp dữ liệu, nó sẽ gọi `LearningInterface` để Query `FlashcardSet` và `FlashcardItem`.
- Quyền sở hữu (Domain Execution) đối với Schema JSON bên trong Item thuộc về Module riêng (flashcard tự quản lý trường JSON `front`/`back`), nhưng quyền sở hữu lưu trữ RDBMS thuộc về Module `learning`.
