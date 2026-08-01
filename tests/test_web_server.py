"""
Unit & Integration Tests for 3_web_server/main.py FastAPI Route Handlers & Security
Location: tests/test_web_server.py
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_SERVER_DIR = os.path.join(PROJECT_ROOT, "3_web_server")
if WEB_SERVER_DIR not in sys.path:
    sys.path.insert(0, WEB_SERVER_DIR)

try:
    from fastapi import HTTPException
    from main import (
        AdminVerifyRequest,
        WatchlistCreate,
        WatchlistUpdate,
        verify_admin,
        get_admin_password,
        verify_password_header,
        get_app_settings,
        get_watchlist,
        create_watchlist_item,
        update_watchlist_item,
        delete_watchlist_item,
        get_cron_logs,
        get_analysis_logs,
        get_error_logs,
        get_logs_by_type,
        clear_logs,
        get_report,
        get_dates,
        get_reprocess_status,
        get_active_reprocess_status,
        get_access_logs,
        get_connection_analytics
    )
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@unittest.skipUnless(HAS_FASTAPI, "FastAPI not installed in local environment")
class TestWebServerHandlers(unittest.TestCase):

    def setUp(self):
        self.admin_password = get_admin_password()

    # ══════════════════════════════════════════════════════════
    # 1. AUTHENTICATION & SECURITY TESTS
    # ══════════════════════════════════════════════════════════

    def test_verify_admin_valid_password(self):
        req = AdminVerifyRequest(password=self.admin_password)
        res = verify_admin(req)
        self.assertEqual(res.get("status"), "ok")

    def test_verify_admin_invalid_password(self):
        req = AdminVerifyRequest(password="invalid_password_12345")
        with self.assertRaises(HTTPException) as ctx:
            verify_admin(req)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_verify_password_header_valid(self):
        # Should not raise exception
        verify_password_header(x_admin_password=self.admin_password)

    def test_verify_password_header_invalid(self):
        with self.assertRaises(HTTPException) as ctx:
            verify_password_header(x_admin_password="wrong_password")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_security_path_traversal_blocked(self):
        """Security test: verify path traversal parameters trigger HTTP 400 Bad Request."""
        with self.assertRaises(HTTPException) as ctx:
            get_report(ticker="../../etc", date="passwd")
        self.assertEqual(ctx.exception.status_code, 400)

    # ══════════════════════════════════════════════════════════
    # 2. WATCHLIST CRUD ROUTE TESTS
    # ══════════════════════════════════════════════════════════

    def test_get_watchlist_returns_list(self):
        items = get_watchlist()
        self.assertIsInstance(items, list)

    def test_watchlist_crud_lifecycle(self):
        test_ticker = "UNITTEST_TICKER"

        # 1. Create
        item = WatchlistCreate(ticker=test_ticker, company_name="UnitTest Company", lang="TR")
        try:
            res_create = create_watchlist_item(item, x_admin_password=self.admin_password)
            self.assertIn("added successfully", res_create.get("message", ""))
        except HTTPException as e:
            self.assertEqual(e.status_code, 400)  # Exists already

        # 2. Update
        update_item = WatchlistUpdate(company_name="Updated UnitTest Company", is_active=1)
        res_update = update_watchlist_item(test_ticker, update_item, x_admin_password=self.admin_password)
        self.assertIn("updated successfully", res_update.get("message", ""))

        # 3. Delete
        res_del = delete_watchlist_item(test_ticker, x_admin_password=self.admin_password)
        self.assertIn("removed", res_del.get("message", ""))

    # ══════════════════════════════════════════════════════════
    # 3. APP SETTINGS & LOG ENDPOINT TESTS
    # ══════════════════════════════════════════════════════════

    def test_get_app_settings(self):
        settings = get_app_settings(x_admin_password=self.admin_password)
        self.assertIn("ADMIN_PASSWORD", settings)
        self.assertEqual(settings["ADMIN_PASSWORD"], "••••••••")
        self.assertIn("ADMIN_PASSWORD_IS_SET", settings)
        self.assertIn("LLM_API_KEY_IS_SET", settings)
        self.assertTrue(settings["LLM_API_KEY"].startswith("••••"))

    def test_verify_admin_rate_limiter(self):
        req = AdminVerifyRequest(password="WRONG_PASSWORD_123")
        ip = "10.99.99.99"
        # 5 failed attempts raise 401
        for _ in range(5):
            with self.assertRaises(HTTPException) as ctx:
                verify_admin(req, x_forwarded_for=ip)
            self.assertEqual(ctx.exception.status_code, 401)
        # 6th failed attempt raises 429 Too Many Requests
        with self.assertRaises(HTTPException) as ctx:
            verify_admin(req, x_forwarded_for=ip)
        self.assertEqual(ctx.exception.status_code, 429)

    def test_get_cron_logs(self):
        logs = get_cron_logs(x_admin_password=self.admin_password)
        self.assertIn("log", logs)

    def test_get_analysis_logs(self):
        logs = get_analysis_logs(x_admin_password=self.admin_password)
        self.assertIn("log", logs)

    def test_get_error_logs(self):
        logs = get_error_logs(x_admin_password=self.admin_password)
        self.assertIn("log", logs)

    def test_get_logs_by_type(self):
        analysis_logs = get_logs_by_type("analysis", x_admin_password=self.admin_password)
        self.assertIn("log", analysis_logs)
        cron_logs = get_logs_by_type("cron", x_admin_password=self.admin_password)
        self.assertIn("log", cron_logs)
        with self.assertRaises(HTTPException) as ctx:
            get_logs_by_type("invalid_type", x_admin_password=self.admin_password)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_clear_logs_live(self):
        res = clear_logs("live", x_admin_password=self.admin_password)
        self.assertEqual(res.get("status"), "ok")

    def test_clear_logs_errors(self):
        res = clear_logs("errors", x_admin_password=self.admin_password)
        self.assertEqual(res.get("status"), "ok")

    def test_get_reprocess_status_idle(self):
        status = get_reprocess_status("NON_EXISTENT_TICKER")
        self.assertEqual(status.get("status"), "IDLE")

    def test_get_active_reprocess_status(self):
        status = get_active_reprocess_status(x_admin_password=self.admin_password)
        self.assertIn("active", status)
        self.assertIn("status", status)

    def test_get_access_logs(self):
        logs = get_access_logs(x_admin_password=self.admin_password)
        self.assertIn("log", logs)

    def test_get_connection_analytics(self):
        analytics = get_connection_analytics(x_admin_password=self.admin_password)
        self.assertIn("total_unique_ips", analytics)
        self.assertIn("total_requests", analytics)
        self.assertIn("ip_stats", analytics)


if __name__ == "__main__":
    unittest.main()
