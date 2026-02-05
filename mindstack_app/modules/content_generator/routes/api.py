from flask import jsonify, request, current_app
import json
from sqlalchemy import func
from datetime import datetime, timedelta
from mindstack_app.core.extensions import db
from mindstack_app.models import LearningItem
from .. import blueprint
from ..models import GenerationLog
from ..interface import generate_text, generate_audio, generate_image
from ..exceptions import InvalidRequestError

@blueprint.route('/api/generate/text', methods=['POST'])
def api_gen_text():
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "Missing prompt"}), 400
            
        log = generate_text(data['prompt'], requester_module="api")
        return jsonify({"message": "Task queued", "log_id": log.id, "task_id": log.task_id}), 202
    except InvalidRequestError as e:
        return jsonify({"error": str(e)}), 400

@blueprint.route('/api/generate/audio', methods=['POST'])
def api_gen_audio():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Missing text"}), 400
            
        log = generate_audio(data['text'], voice_id=data.get('voice_id', 'default'), requester_module="api")
        return jsonify({"message": "Task queued", "log_id": log.id, "task_id": log.task_id}), 202
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@blueprint.route('/api/cleanup', methods=['POST'])
def cleanup_zombies():
    """Force fail all stuck tasks regardless of time."""
    # We remove the 30m threshold because user wants manual force clean
    stuck_tasks = GenerationLog.query.filter(
        GenerationLog.status.in_(['processing', 'pending'])
    ).all()
    
    count = 0
    for task in stuck_tasks:
        task.status = 'failed'
        task.error_message = f"Force cleanup by user at {datetime.utcnow().strftime('%H:%M:%S')}"
        task.stop_requested = True
        count += 1
    
    db.session.commit()
    return jsonify({"success": True, "cleaned": count})

@blueprint.route('/api/sessions', methods=['GET'])
def list_sessions():
    """Lấy danh sách các session gần đây kèm thống kê nhanh."""
    sessions = db.session.query(
        GenerationLog.session_id,
        func.max(GenerationLog.session_name).label('session_name'),
        func.min(GenerationLog.created_at).label('start_time'),
        func.count(GenerationLog.id).label('total_tasks'),
        func.sum(db.case((GenerationLog.status == 'completed', 1), else_=0)).label('completed_tasks'),
        func.sum(db.case((GenerationLog.status == 'failed', 1), else_=0)).label('failed_tasks'),
    ).filter(GenerationLog.session_id.isnot(None))\
     .group_by(GenerationLog.session_id)\
     .order_by(func.min(GenerationLog.created_at).desc())\
     .limit(10).all()

    result = []
    for s in sessions:
        total = s.total_tasks or 0
        completed = s.completed_tasks or 0
        failed = s.failed_tasks or 0
        done = completed + failed
        progress = int((done / total) * 100) if total > 0 else 0
        
        if progress < 100: status = "Running"
        elif failed == total: status = "Failed"
        elif failed > 0: status = "Partial"
        else: status = "Finished"

        result.append({
            "session_id": s.session_id,
            "session_name": s.session_name or s.session_id,
            "start_time": s.start_time.strftime('%H:%M %d/%m') if s.start_time else "Unknown",
            "total": total,
            "completed": completed,
            "failed": failed,
            "progress": progress,
            "status": status,
            "is_active": progress < 100
        })
    return jsonify(result)

@blueprint.route('/api/session/<session_id>/details', methods=['GET'])
def get_session_details(session_id):
    logs = GenerationLog.query.filter_by(session_id=session_id).order_by(GenerationLog.created_at.asc()).all()
    items_map = {}
    for log in logs:
        try:
            iid = log.item_id
            if iid is None: continue

            if iid not in items_map:
                clean_title = log.item_title or f"Item #{iid}"
                if ']' in clean_title:
                    clean_title = clean_title.split(']', 1)[-1].strip()
                items_map[iid] = {
                    "item_id": iid,
                    "item_title": clean_title,
                    "tasks": { "front_audio": None, "back_audio": None, "ai": None }
                }
            
            payload = {}
            if log.input_payload:
                try: payload = json.loads(log.input_payload)
                except: pass
            side = payload.get('side', 'front')
            
            task_data = {
                "id": log.id,
                "status": log.status,
                "error": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "execution_time_ms": log.execution_time_ms,
                "cost_tokens": log.cost_tokens
            }
            if log.request_type == 'audio':
                if side == 'front': items_map[iid]["tasks"]["front_audio"] = task_data
                else: items_map[iid]["tasks"]["back_audio"] = task_data
            elif log.request_type == 'text':
                items_map[iid]["tasks"]["ai"] = task_data
        except Exception as e:
            current_app.logger.error(f"Error parsing log {log.id}: {e}")
            continue

    return jsonify({
        "session_id": session_id,
        "items": list(items_map.values())
    })

@blueprint.route('/api/session/<session_id>/status', methods=['GET'])
def get_session_status(session_id):
    logs = GenerationLog.query.filter_by(session_id=session_id).all()
    if not logs: return jsonify({"error": "Not found"}), 404
    total = len(logs)
    completed = sum(1 for log in logs if log.status == 'completed')
    failed = sum(1 for log in logs if log.status == 'failed')
    return jsonify({
        "session_id": session_id,
        "total": total,
        "completed": completed,
        "failed": failed,
        "progress_percent": int(((completed + failed) / total) * 100) if total > 0 else 0,
        "is_finished": (completed + failed) == total
    })

@blueprint.route('/api/session/<session_id>/stop', methods=['POST'])
def stop_session(session_id):
    """Mark tasks as stopped. Pending tasks are failed immediately."""
    tasks = GenerationLog.query.filter_by(session_id=session_id).filter(
        GenerationLog.status.in_(['pending', 'processing'])
    ).all()
    stopped_count = 0
    for task in tasks:
        task.stop_requested = True
        if task.status == 'pending':
            task.status = 'failed'
            task.error_message = "Force cancelled by user."
        stopped_count += 1
    db.session.commit()
    return jsonify({"success": True, "message": f"Stopped {stopped_count} tasks."})

@blueprint.route('/api/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session and its logs."""
    try:
        deleted_count = GenerationLog.query.filter_by(session_id=session_id).delete()
        db.session.commit()
        return jsonify({"success": True, "message": f"Deleted {deleted_count} tasks."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@blueprint.route('/api/item/<int:item_id>/preview', methods=['GET'])
def get_item_preview(item_id):
    item = LearningItem.query.get_or_404(item_id)
    content = item.content or {}
    custom_data = item.custom_data or {}
    
    # Enhanced Text Extraction
    front = content.get('front') or content.get('question') or content.get('term') or "N/A"
    back = content.get('back') or content.get('answer') or content.get('definition') or "N/A"
    
    front_audio = content.get('front_audio_url') or custom_data.get('front_audio_url')
    back_audio = content.get('back_audio_url') or custom_data.get('back_audio_url')
    generic_audio = content.get('audio_url') or custom_data.get('audio_url')
    
    tags = item.custom_data.get('tags', []) if item.custom_data else []
    
    return jsonify({
        "item_id": item.item_id,
        "type": item.item_type,
        "front": front,
        "back": back,
        "front_audio": front_audio or generic_audio,
        "back_audio": back_audio,
        "ai_explanation": item.ai_explanation,
        "tags": tags
    })
