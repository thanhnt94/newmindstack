# File: newmindstack/mindstack_app/modules/content_management/quizzes/routes.py
# Phiên bản: 3.5
# Mục đích: Xử lý các route liên quan đến quản lý bộ câu hỏi (LearningContainer loại 'QUIZ_SET')
#           Bao gồm tạo, xem, chỉnh sửa, xóa bộ câu hỏi và các câu hỏi (LearningItem loại 'QUIZ_MCQ')
#           Áp dụng logic phân quyền để kiểm tra người dùng có quyền truy cập/chỉnh sửa hay không.
#           Bổ sung logic để phục vụ nội dung riêng cho yêu cầu AJAX từ dashboard tổng quan.
#           Đã sửa lỗi BuildError bằng cách cập nhật tên endpoint trong url_for.
#           Đã khắc phục ModuleNotFoundError bằng cách sửa đường dẫn import models.
#           ĐÃ SỬA: Chuyển hướng sau khi thêm/sửa/xóa về content_dashboard và chọn tab đúng.
#           ĐÃ SỬA: Điều chỉnh để trả về JSON cho các yêu cầu AJAX khi thêm/sửa/xóa bộ.
#           ĐÃ SỬA: Render template bare form cho yêu cầu GET từ modal, full form cho non-modal GET.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from ..forms import QuizSetForm, QuizItemForm # Import form từ thư mục cha (content_management)
from ....models import db, LearningContainer, LearningItem, ContainerContributor, User # Đã thêm một dấu chấm

# Định nghĩa Blueprint cho quản lý bộ câu hỏi
quizzes_bp = Blueprint('content_management_quizzes', __name__,
                        template_folder='../templates/quizzes')

@quizzes_bp.route('/quizzes')
@login_required
def list_quiz_sets():
    """
    Hiển thị danh sách các bộ câu hỏi mà người dùng hiện tại có quyền truy cập.
    Admin có thể thấy tất cả các bộ câu hỏi.
    Người dùng thông thường chỉ thấy bộ câu hỏi do mình tạo hoặc được cấp quyền chỉnh sửa.
    Nếu yêu cầu là AJAX, chỉ trả về phần danh sách bộ câu hỏi.
    """
    quiz_sets = []
    if current_user.user_role == 'admin':
        # Admin thấy tất cả các bộ câu hỏi
        quiz_sets = LearningContainer.query.filter_by(container_type='QUIZ_SET').all()
    else:
        # Người dùng thường thấy bộ câu hỏi của mình tạo hoặc được cấp quyền
        user_id = current_user.user_id
        
        # Lấy các container_id mà người dùng hiện tại là người tạo
        created_sets_query = LearningContainer.query.filter_by(
            creator_user_id=user_id,
            container_type='QUIZ_SET'
        )

        # Lấy các container_id mà người dùng hiện tại được cấp quyền chỉnh sửa
        contributed_sets_query = LearningContainer.query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor',
            LearningContainer.container_type == 'QUIZ_SET'
        )
        
        # Kết hợp hai truy vấn để lấy danh sách các bộ câu hỏi duy nhất
        quiz_sets = created_sets_query.union(contributed_sets_query).all()

    # Kiểm tra nếu đây là yêu cầu AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Nếu là AJAX, chỉ render phần danh sách các bộ câu hỏi
        return render_template('_quiz_sets_list.html', quiz_sets=quiz_sets)
    else:
        # Nếu không phải AJAX, render toàn bộ trang như bình thường
        return render_template('quiz_sets.html', quiz_sets=quiz_sets)

@quizzes_bp.route('/quizzes/add', methods=['GET', 'POST'])
@login_required
def add_quiz_set():
    """
    Thêm một bộ câu hỏi mới.
    Chỉ người dùng đã đăng nhập mới có thể thêm bộ câu hỏi.
    Người tạo bộ câu hỏi sẽ tự động là creator_user_id.
    """
    form = QuizSetForm()
    if form.validate_on_submit():
        new_set = LearningContainer(
            creator_user_id=current_user.user_id,
            container_type='QUIZ_SET',
            title=form.title.data,
            description=form.description.data,
            tags=form.tags.data,
            is_public=form.is_public.data
        )
        db.session.add(new_set)
        db.session.commit()
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Bộ câu hỏi mới đã được tạo thành công!'})
        else:
            flash('Bộ câu hỏi mới đã được tạo thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    # ĐÃ SỬA: Trả về JSON chứa lỗi nếu là AJAX POST và form không hợp lệ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    # ĐÃ SỬA: Nếu là GET request VÀ có tham số is_modal=true, render bare template
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_set_bare.html', form=form, title='Thêm Bộ câu hỏi mới')
    return render_template('add_edit_quiz_set.html', form=form, title='Thêm Bộ câu hỏi mới')

@quizzes_bp.route('/quizzes/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz_set(set_id):
    """
    Chỉnh sửa thông tin bộ câu hỏi.
    Chỉ creator_user_id hoặc người dùng được cấp quyền 'editor' mới có thể chỉnh sửa.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)

    # Kiểm tra quyền chỉnh sửa
    if current_user.user_role != 'admin' and \
       quiz_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại flash và abort
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa bộ câu hỏi này.'}), 403
        else:
            abort(403) # Forbidden nếu không có quyền

    form = QuizSetForm(obj=quiz_set) # Điền dữ liệu hiện có vào form
    if form.validate_on_submit():
        quiz_set.title = form.title.data
        quiz_set.description = form.description.data
        quiz_set.tags = form.tags.data
        quiz_set.is_public = form.is_public.data
        db.session.commit()
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Bộ câu hỏi đã được cập nhật thành công!'})
        else:
            flash('Bộ câu hỏi đã được cập nhật thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    # ĐÃ SỬA: Trả về JSON chứa lỗi nếu là AJAX POST và form không hợp lệ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    # ĐÃ SỬA: Nếu là GET request VÀ có tham số is_modal=true, render bare template
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_set_bare.html', form=form, title='Sửa Bộ câu hỏi', quiz_set=quiz_set)
    return render_template('add_edit_quiz_set.html', form=form, title='Sửa Bộ câu hỏi', quiz_set=quiz_set)

@quizzes_bp.route('/quizzes/delete/<int:set_id>', methods=['POST'])
@login_required
def delete_quiz_set(set_id):
    """
    Xóa một bộ câu hỏi.
    Chỉ creator_user_id hoặc admin mới có thể xóa bộ câu hỏi.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)

    # Kiểm tra quyền xóa
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại flash và abort
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền xóa bộ câu hỏi này.'}), 403
        else:
            abort(403) # Forbidden nếu không có quyền

    db.session.delete(quiz_set)
    db.session.commit()
    
    # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Bộ câu hỏi đã được xóa thành công!'})
    else:
        flash('Bộ câu hỏi đã được xóa thành công!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='quizzes'))

@quizzes_bp.route('/quizzes/<int:set_id>/items')
@login_required
def list_quiz_items(set_id):
    """
    Hiển thị danh sách các câu hỏi thuộc một bộ câu hỏi cụ thể.
    Người dùng cần có quyền xem bộ câu hỏi đó.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)

    # Kiểm tra quyền xem bộ câu hỏi: public, là người tạo, hoặc là contributor
    if not quiz_set.is_public and \
       current_user.user_role != 'admin' and \
       quiz_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id).first():
        abort(403) # Forbidden nếu không có quyền

    quiz_items = LearningItem.query.filter_by(
        container_id=quiz_set.container_id,
        item_type='QUIZ_MCQ' # Giả định mặc định là QUIZ_MCQ
    ).order_by(LearningItem.order_in_container).all()

    # Xác định quyền chỉnh sửa để truyền xuống template
    can_edit = False
    if current_user.user_role == 'admin' or \
       quiz_set.creator_user_id == current_user.user_id or \
       ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        can_edit = True

    return render_template('quiz_items.html', quiz_set=quiz_set, quiz_items=quiz_items, can_edit=can_edit)

@quizzes_bp.route('/quizzes/<int:set_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_quiz_item(set_id):
    """
    Thêm câu hỏi mới vào một bộ câu hỏi.
    Chỉ người tạo bộ câu hỏi hoặc người dùng được cấp quyền 'editor' mới có thể thêm.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)

    # Kiểm tra quyền chỉnh sửa
    if current_user.user_role != 'admin' and \
       quiz_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại flash và abort
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền thêm câu hỏi vào bộ này.'}), 403
        else:
            abort(403) # Forbidden nếu không có quyền

    form = QuizItemForm()
    if form.validate_on_submit():
        # Tìm số thứ tự lớn nhất hiện có và tăng lên 1
        max_order = db.session.query(db.func.max(LearningItem.order_in_container)).filter_by(
            container_id=set_id,
            item_type='QUIZ_MCQ'
        ).scalar()
        new_order = (max_order or 0) + 1

        new_item = LearningItem(
            container_id=set_id,
            item_type='QUIZ_MCQ', # Giả định mặc định là QUIZ_MCQ
            content={
                'question_text': form.question_text.data,
                'options': {
                    'A': form.option_a.data,
                    'B': form.option_b.data,
                    'C': form.option_c.data,
                    'D': form.option_d.data
                },
                'correct_answer': form.correct_answer.data,
                'explanation': form.explanation.data
            }, # Lưu nội dung dưới dạng JSON
            order_in_container=new_order
        )
        db.session.add(new_item)
        db.session.commit()
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Câu hỏi mới đã được thêm thành công!'})
        else:
            flash('Câu hỏi mới đã được thêm thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    # ĐÃ SỬA: Trả về JSON chứa lỗi nếu là AJAX POST và form không hợp lệ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    # ĐÃ SỬA: Nếu là GET request VÀ có tham số is_modal=true, render bare template
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_item_bare.html', form=form, quiz_set=quiz_set, title='Thêm Câu hỏi')
    return render_template('add_edit_quiz_item.html', form=form, quiz_set=quiz_set, title='Thêm Câu hỏi')

@quizzes_bp.route('/quizzes/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz_item(set_id, item_id):
    """
    Chỉnh sửa một câu hỏi cụ thể trong bộ câu hỏi.
    Chỉ người tạo bộ câu hỏi hoặc người dùng được cấp quyền 'editor' mới có thể chỉnh sửa.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    quiz_item = LearningItem.query.get_or_404(item_id)

    # Kiểm tra quyền chỉnh sửa
    if current_user.user_role != 'admin' and \
       quiz_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại flash và abort
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa câu hỏi này.'}), 403
        else:
            abort(403) # Forbidden nếu không có quyền

    form = QuizItemForm(
        question_text=quiz_item.content.get('question_text'),
        option_a=quiz_item.content.get('options', {}).get('A'),
        option_b=quiz_item.content.get('options', {}).get('B'),
        option_c=quiz_item.content.get('options', {}).get('C'),
        option_d=quiz_item.content.get('options', {}).get('D'),
        correct_answer=quiz_item.content.get('correct_answer'),
        explanation=quiz_item.content.get('explanation')
    )
    
    if form.validate_on_submit():
        quiz_item.content = {
            'question_text': form.question_text.data,
            'options': {
                'A': form.option_a.data,
                'B': form.option_b.data,
                'C': form.option_c.data,
                'D': form.option_d.data
            },
            'correct_answer': form.correct_answer.data,
            'explanation': form.explanation.data
        }
        db.session.commit()
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Câu hỏi đã được cập nhật thành công!'})
        else:
            flash('Câu hỏi đã được cập nhật thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    # ĐÃ SỬA: Trả về JSON chứa lỗi nếu là AJAX POST và form không hợp lệ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    # ĐÃ SỬA: Nếu là GET request VÀ có tham số is_modal=true, render bare template
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_item_bare.html', form=form, quiz_set=quiz_set, quiz_item=quiz_item, title='Chỉnh sửa Câu hỏi')
    return render_template('add_edit_quiz_item.html', form=form, quiz_set=quiz_set, quiz_item=quiz_item, title='Chỉnh sửa Câu hỏi')

@quizzes_bp.route('/quizzes/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_quiz_item(set_id, item_id):
    """
    Xóa một câu hỏi cụ thể trong bộ câu hỏi.
    Chỉ người tạo bộ câu hỏi hoặc người dùng được cấp quyền 'editor' mới có thể xóa.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    quiz_item = LearningItem.query.get_or_404(item_id)

    # Kiểm tra quyền xóa
    if current_user.user_role != 'admin' and \
       quiz_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại flash và abort
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền xóa câu hỏi này.'}), 403
        else:
            flash('Bạn không có quyền xóa câu hỏi này.', 'danger')
            abort(403)
    
    db.session.delete(quiz_item)
    db.session.commit()
    
    # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Câu hỏi đã được xóa thành công!'})
    else:
        flash('Câu hỏi đã được xóa thành công!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
