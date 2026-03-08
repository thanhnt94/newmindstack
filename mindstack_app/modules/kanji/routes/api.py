from flask import Blueprint, request

kanji_api_bp = Blueprint('kanji_api', __name__, url_prefix='/api/kanji')

@kanji_api_bp.route('/<char>/similar')
def api_get_similar(char):
    from ..interface import KanjiInterface
    results = KanjiInterface.get_similar_kanji(char)
    return {"results": results}

@kanji_api_bp.route('/<char>/details')
def api_get_details(char):
    from ..interface import KanjiInterface
    details = KanjiInterface.get_details(char)
    if details:
        decompositions = KanjiInterface.get_decompositions(char)
        details['decompositions'] = decompositions
    return {"details": details}

@kanji_api_bp.route('/<char>/components')
def api_get_components(char):
    from ..interface import KanjiInterface
    components = KanjiInterface.get_components(char)
    return {"components": components}
