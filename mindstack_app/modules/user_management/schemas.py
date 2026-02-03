# File: mindstack_app/modules/user_management/schemas.py
# Refactored: Removed marshmallow dependency, using plain dict mapping for now.

class UserSchema:
    @staticmethod
    def dump(obj):
        if not obj:
            return None
        
        from mindstack_app.modules.auth.models import User
        
        return {
            'user_id': obj.user_id,
            'username': obj.username,
            'email': obj.email,
            'user_role': obj.user_role,
            'role_label': User.ROLE_LABELS.get(obj.user_role, obj.user_role),
            'avatar_url': obj.avatar_url,
            'total_score': obj.total_score or 0,
            'last_seen': obj.last_seen.isoformat() if obj.last_seen else None,
            'timezone': obj.timezone or 'UTC'
        }

class UserProfileSchema(UserSchema):
    @staticmethod
    def dump(obj):
        data = UserSchema.dump(obj)
        if data:
            # Add profile specific fields if any
            # assuming joined_at might be created_at if we add it to model
            # for now just return the base data
            pass
        return data