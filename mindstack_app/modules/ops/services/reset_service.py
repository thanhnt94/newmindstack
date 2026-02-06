from mindstack_app.models import (
    db, User, ItemMemoryState, LearningItem, LearningContainer, 
    LearningSession, UserItemMarker, UserContainerState, ContainerContributor, LearningGroup
)
from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
from sqlalchemy import text, distinct, or_

class ResetService:
    @staticmethod
    def reset_learning_progress(user_id=None):
        """
        Xóa toàn bộ tiến độ học tập, lịch sử ôn tập và phiên học.
        """
        try:
            if user_id:
                # Dữ liệu phụ thuộc vào User
                LearningHistoryInterface.delete_user_history(user_id)
                ItemMemoryState.query.filter_by(user_id=user_id).delete()
                LearningSession.query.filter_by(user_id=user_id).delete()
                UserItemMarker.query.filter_by(user_id=user_id).delete()
                UserContainerState.query.filter_by(user_id=user_id).delete()
            else:
                # Xóa toàn bộ
                # REFAC: Direct model access via interface special method for admin/ops
                StudyLog = LearningHistoryInterface.get_model_class()
                db.session.query(StudyLog).delete()
                
                db.session.query(ItemMemoryState).delete()
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
            StudyLog = LearningHistoryInterface.get_model_class()
            db.session.query(StudyLog).delete()
            
            db.session.query(ItemMemoryState).delete()
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

    @staticmethod
    def reset_user_container_progress(user_id: int, container_id: int):
        """
        Selective Reset: Xóa toàn bộ tiến độ, lịch sử, điểm và session 
        của User A tại Container B.
        """
        try:
            # 1. Lấy danh sách Item ID thuộc Container
            item_ids = [item.item_id for item in LearningItem.query.filter_by(container_id=container_id).all()]
            
            if item_ids:
                # 2. Xóa StudyLog & ItemMemoryState & Markers & ScoreLog (theo item)
                
                # REFAC: Use specialized deletion logic or raw query via model class if interface doesn't support item-level bulk delete yet
                # Currently creating granular methods in interface for every edge case is overkill, so allowing restricted Model access
                StudyLog = LearningHistoryInterface.get_model_class()
                db.session.query(StudyLog).filter(StudyLog.user_id == user_id, StudyLog.item_id.in_(item_ids)).delete(synchronize_session=False)
                
                ItemMemoryState.query.filter(ItemMemoryState.user_id == user_id, ItemMemoryState.item_id.in_(item_ids)).delete(synchronize_session=False)
                UserItemMarker.query.filter(UserItemMarker.user_id == user_id, UserItemMarker.item_id.in_(item_ids)).delete(synchronize_session=False)
                # REFAC: Use Interface for ScoreLog
                from mindstack_app.modules.gamification.interface import delete_items_gamification_data
                delete_items_gamification_data(user_id, item_ids)

            # 3. Xóa LearningSession (Xử lý JSON set_id_data)
            # Vì set_id_data là JSON, ta lọc và xóa các session liên quan
            sessions = LearningSession.query.filter_by(user_id=user_id).all()
            for sess in sessions:
                sid = sess.set_id_data
                should_delete = False
                if isinstance(sid, int) and sid == container_id:
                    should_delete = True
                elif isinstance(sid, list) and container_id in sid:
                    should_delete = True
                
                if should_delete:
                    db.session.delete(sess)

            # 4. Xóa UserContainerState
            UserContainerState.query.filter_by(user_id=user_id, container_id=container_id).delete()

            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_discovery_data():
        """
        Trả về danh sách User có dữ liệu học tập để hiển thị trong Select box.
        """
        # User có ItemMemoryState hoặc UserContainerState
        user_ids_with_memory = db.session.query(ItemMemoryState.user_id).distinct()
        user_ids_with_state = db.session.query(UserContainerState.user_id).distinct()
        
        final_user_ids = db.session.query(User.user_id, User.username, User.email)\
            .filter(User.user_id.in_(user_ids_with_memory.union(user_ids_with_state)))\
            .all()
            
        return [
            {'user_id': u.user_id, 'username': u.username, 'email': u.email}
            for u in final_user_ids
        ]

    @staticmethod
    def get_user_containers_discovery(user_id: int):
        """
        Trả về danh sách Container mà User này đã tham gia học.
        """
        # Lấy container_id từ UserContainerState
        container_ids = db.session.query(UserContainerState.container_id)\
            .filter_by(user_id=user_id).distinct().all()
        
        ids = [c[0] for c in container_ids]
        
        # Thêm các container mà user có ItemMemoryState (phòng trường hợp UserContainerState bị thiếu)
        item_memory_containers = db.session.query(LearningItem.container_id)\
            .join(ItemMemoryState, ItemMemoryState.item_id == LearningItem.item_id)\
            .filter(ItemMemoryState.user_id == user_id).distinct().all()
        
        ids.extend([c[0] for c in item_memory_containers if c[0] not in ids])
        
        if not ids:
            return []
            
        containers = LearningContainer.query.filter(LearningContainer.container_id.in_(ids)).all()
        return [
            {'container_id': c.container_id, 'title': c.title, 'type': c.container_type}
            for c in containers
        ]
