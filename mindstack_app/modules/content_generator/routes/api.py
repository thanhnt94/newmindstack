from flask import jsonify, request
from .. import blueprint
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
