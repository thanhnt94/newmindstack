import unittest
from unittest.mock import MagicMock, patch
from mindstack_app.modules.access_control.services.permission_service import PermissionService
from mindstack_app.modules.access_control.logics.policies import (
    ROLE_FREE, ROLE_USER, ROLE_ADMIN, 
    CAN_EXPORT_EXCEL, LIMIT_FLASHCARDS, PolicyValues
)
from mindstack_app.modules.access_control.exceptions import QuotaExceededError

class TestAccessControlFlows(unittest.TestCase):
    
    def setUp(self):
        self.mock_user = MagicMock()
        self.mock_user.user_role = ROLE_FREE
        
    def test_permission_check_free_user(self):
        """Test that FREE user cannot export excel."""
        self.mock_user.user_role = ROLE_FREE
        can_export = PermissionService.check_permission(self.mock_user, CAN_EXPORT_EXCEL)
        self.assertFalse(can_export)
        
    def test_permission_check_premium_user(self):
        """Test that PREMIUM user CAN export excel."""
        self.mock_user.user_role = ROLE_USER
        can_export = PermissionService.check_permission(self.mock_user, CAN_EXPORT_EXCEL)
        self.assertTrue(can_export)
        
    def test_quota_check_limit_exceeded(self):
        """Test quota enforcement raises error."""
        self.mock_user.user_role = ROLE_FREE
        # Limit is 50
        with self.assertRaises(QuotaExceededError):
            PermissionService.check_quota(self.mock_user, LIMIT_FLASHCARDS, current_usage=51)
            
    def test_quota_check_limit_ok(self):
        """Test quota enforcement passes."""
        self.mock_user.user_role = ROLE_FREE
        # Limit is 50
        result = PermissionService.check_quota(self.mock_user, LIMIT_FLASHCARDS, current_usage=40)
        self.assertTrue(result)
        
    def test_admin_unlimited(self):
        """Test admin has unlimited quota."""
        self.mock_user.user_role = ROLE_ADMIN
        # Even with huge usage
        result = PermissionService.check_quota(self.mock_user, LIMIT_FLASHCARDS, current_usage=999999)
        self.assertTrue(result)
        
if __name__ == '__main__':
    unittest.main()
