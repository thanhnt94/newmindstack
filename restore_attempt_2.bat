
@echo off
git show 3a9889c6c8d792f2b93d5ad7e3c6da34c4f48076:mindstack_app/modules/learning/sub_modules/quiz/static/quiz/css/session_single.css > session_single_legacy_nested.css
git show 3a9889c6c8d792f2b93d5ad7e3c6da34c4f48076:mindstack_app/modules/learning/quiz/static/quiz/css/session_single.css > session_single_legacy_direct.css
git show 3a9889c6c8d792f2b93d5ad7e3c6da34c4f48076:mindstack_app/modules/learning/sub_modules/quiz/static/quiz/js/session.js > session_js_nested.js
git show 3a9889c6c8d792f2b93d5ad7e3c6da34c4f48076:mindstack_app/modules/learning/quiz/static/quiz/js/session.js > session_js_direct.js
