# File: Mindstack/web/mindstack_app/utils/search.py
# Version: 2.0
# ĐÃ SỬA: Cập nhật hàm apply_search_filter để hỗ trợ tìm kiếm theo một trường cụ thể (search_field).

from sqlalchemy import or_

def apply_search_filter(query, search_query, search_field_map, search_field='all'):
    """
    Áp dụng bộ lọc tìm kiếm cho một truy vấn SQLAlchemy, có hỗ trợ tìm kiếm theo trường cụ thể.

    Args:
        query: Đối tượng truy vấn SQLAlchemy.
        search_query (str): Chuỗi tìm kiếm từ người dùng.
        search_field_map (dict): Dictionary ánh xạ tên trường (ví dụ: 'title') tới cột SQLAlchemy (ví dụ: LearningContainer.title).
        search_field (str): Tên trường được chọn để tìm kiếm (ví dụ: 'title', 'description', 'all').

    Returns:
        query: Đối tượng truy vấn SQLAlchemy đã được áp dụng bộ lọc.
    """
    if not search_query:
        return query

    search_terms = search_query.split()
    conditions = []
    
    fields_to_search = []
    if search_field != 'all' and search_field in search_field_map:
        # Nếu người dùng chọn một trường cụ thể, chỉ tìm trên trường đó
        fields_to_search.append(search_field_map[search_field])
    else:
        # Mặc định hoặc nếu chọn 'all', tìm trên tất cả các trường
        fields_to_search = search_field_map.values()

    for term in search_terms:
        for field in fields_to_search:
            conditions.append(field.ilike(f'%{term}%'))
    
    if conditions:
        query = query.filter(or_(*conditions))
            
    return query
