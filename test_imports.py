# Test import
import sys
sys.path.insert(0, 'c:/Code/MindStack/newmindstack')

try:
    from mindstack_app.modules.learning.routes.stats_api import stats_api_bp
    print(f"✅ stats_api_bp imported: {stats_api_bp}")
except Exception as e:
    print(f"❌ Failed to import stats_api: {e}")

try:
    from mindstack_app.modules.learning.routes.dashboard import dashboard_bp
    print(f"✅ dashboard_bp imported: {dashboard_bp}")
except Exception as e:
    print(f"❌ Failed to import dashboard: {e}")

try:
    from mindstack_app.modules.learning import routes
    print(f"✅ routes module: {routes}")
    print(f"✅ learning_bp: {routes.learning_bp}")
except Exception as e:
    print(f"❌ Failed: {e}")
