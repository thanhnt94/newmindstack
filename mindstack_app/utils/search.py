# File: Mindstack/web/mindstack_app/utils/search.py
# Version: 1.0
# Mục đích: Cung cấp hàm tiện ích để áp dụng bộ lọc tìm kiếm cho các truy vấn SQLAlchemy.

from sqlalchemy import or_ # Để kết hợp các điều kiện OR

def apply_search_filter(query, search_query, search_fields):
    """
    Áp dụng bộ lọc tìm kiếm cho một truy vấn SQLAlchemy.

    Args:
        query: Đối tượng truy vấn SQLAlchemy.
        search_query (str): Chuỗi tìm kiếm từ người dùng.
        search_fields (list): Danh sách các cột (SQLAlchemy Column) để tìm kiếm.
                              Ví dụ: [User.username, User.email]

    Returns:
        query: Đối tượng truy vấn SQLAlchemy đã được áp dụng bộ lọc.
    """
    if search_query:
        search_terms = search_query.split() # Tách từ khóa theo khoảng trắng
        
        # Tạo danh sách các điều kiện OR cho mỗi từ khóa và mỗi trường
        conditions = []
        for term in search_terms:
            for field in search_fields:
                # Sử dụng ilike để tìm kiếm không phân biệt chữ hoa/thường và khớp một phần
                conditions.append(field.ilike(f'%{term}%'))
        
        # Áp dụng tất cả các điều kiện với OR
        if conditions:
            query = query.filter(or_(*conditions))
            
    return query
