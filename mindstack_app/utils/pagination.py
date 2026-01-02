# File: mindstack_app/modules/shared/utils/pagination.py
# Version: 1.0
# Mục đích: Cung cấp hàm tiện ích để xử lý phân trang cho các truy vấn SQLAlchemy.

from flask import current_app  # Để truy cập cấu hình ITEMS_PER_PAGE


def get_pagination_data(query, page, per_page=None):
    """Thực hiện phân trang cho một truy vấn SQLAlchemy."""

    if per_page is None:
        per_page = current_app.config.get('ITEMS_PER_PAGE', 12)  # Lấy từ config, mặc định 12

    # Sử dụng phương thức paginate của SQLAlchemy
    # error_out=False để không báo lỗi 404 nếu trang không tồn tại
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination
