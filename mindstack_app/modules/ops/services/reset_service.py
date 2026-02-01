from mindstack_app.models import (
    db, User, LearningProgress, ReviewLog, LearningItem, LearningContainer, 
    LearningSession, UserItemMarker, UserContainerState, ContainerContributor, LearningGroup
)
from sqlalchemy import text

class ResetService:
    @staticmethod
    def reset_learning_progress(user_id=None):
        """
        Xóa toàn bộ tiến độ học tập, lịch sử ôn tập và phiên học.
        """
        try:
            if user_id:
                # Dữ liệu phụ thuộc vào User
                ReviewLog.query.filter_by(user_id=user_id).delete()
                LearningProgress.query.filter_by(user_id=user_id).delete()
                LearningSession.query.filter_by(user_id=user_id).delete()
                UserItemMarker.query.filter_by(user_id=user_id).delete()
                UserContainerState.query.filter_by(user_id=user_id).delete()
            else:
                # Xóa toàn bộ
                db.session.query(ReviewLog).delete()
                db.session.query(LearningProgress).delete()
                db.session.query(LearningSession).delete()
                db.session.query(UserItemMarker).delete()
                db.session.query(UserContainerState).delete()
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def reset_content():
        """
        Xóa toàn bộ nội dung học tập (Courses, Flashcards, Quiz).
        Cảnh báo: Hành động này sẽ xóa cả tiến độ học tập liên quan để đảm bảo toàn vẹn dữ liệu.
        """
        try:
            # 1. Xóa dữ liệu học tập phụ thuộc (Tiến độ, Logs, Sessions)
            # Cần xóa trước vì chúng có Foreign Key trỏ tới Item/Container
            db.session.query(ReviewLog).delete()
            db.session.query(LearningProgress).delete()
            db.session.query(UserItemMarker).delete()
            
            # LearningSession không có FK cứng tới Item nhưng chứa ID item trong JSON
            # Nên xóa để tránh tham chiếu rác
            db.session.query(LearningSession).delete()
            
            # 2. Xóa các bảng trạng thái Container của User
            db.session.query(UserContainerState).delete()
            db.session.query(ContainerContributor).delete()
            
            # 3. Xóa Nội dung (Item -> Group -> Container)
            db.session.query(LearningItem).delete()
            db.session.query(LearningGroup).delete()
            db.session.query(LearningContainer).delete()
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def factory_reset():
        """
        Nguy hiểm: Xóa sạch dữ liệu hệ thống về trạng thái ban đầu.
        Giữ lại: Tài khoản Admin và Cấu hình hệ thống (AppSettings).
        """
        try:
            # 1. Gọi reset_content (nó đã bao gồm xóa Progress và Session)
            ResetService.reset_content()
            
            # 2. Xóa Users thường (Giữ lại Admin)
            User.query.filter(User.user_role != 'admin').delete()
            
            # 3. Có thể reset AppSettings về mặc định nếu cần (nhưng code hiện tại giữ lại)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
