# Mindstack App

## Cài đặt
1. Tạo môi trường ảo với Python 3.12 (khuyến nghị) hoặc Python 3.13.
2. Nếu sử dụng Python 3.13, cài thêm gói tương thích `audioop-lts` để khôi phục mô-đun `audioop` mà `pydub` cần:
   ```bash
   pip install audioop-lts
   ```
   Gói này đã được khai báo trong `requirements.txt` với điều kiện `python_version >= "3.13"`, vì vậy chạy `pip install -r requirements.txt` trên Python 3.13 sẽ tự động cài đặt.
3. Cài đặt các phụ thuộc còn lại:
   ```bash
   pip install -r requirements.txt
   ```

## Chạy ứng dụng
Sử dụng lệnh sau sau khi đã cài đặt phụ thuộc:
```bash
python start_mindstack_app.py
```
Ứng dụng sẽ khởi chạy server nội bộ của Mindstack.
