"""
檢查已儲存的 Google session 是否仍有效。

用法：
  venv\\Scripts\\python.exe check_google_login.py
  venv\\Scripts\\python.exe check_google_login.py --headed
"""
import argparse
import sys

from google_session.auth import check_google_login


def main() -> int:
    parser = argparse.ArgumentParser(description="檢查 Google session 是否有效")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="顯示瀏覽器視窗（除錯用）",
    )
    args = parser.parse_args()
    ok = check_google_login(headless=not args.headed)
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
