"""Все проверки сайта одной командой.

    tools/.venv/Scripts/python.exe tools/tests/run_checks.py          # локальная копия site
    tools/.venv/Scripts/python.exe tools/tests/run_checks.py live     # живой https://kryuk24.ru

Для локального режима сам поднимает сервер на 127.0.0.1:8765 (если он еще не запущен).
Через file:// проверять нельзя: геолокация и fetch там зависают.
"""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
SITE = HERE.parents[1] / "site"
sys.path.insert(0, str(HERE))
from common import LIVE, LOCAL  # noqa: E402

CHECKS = ["final_check.py", "cal_check.py", "cities_check.py", "header_check.py", "footer_check.py", "faq_check.py", "message_check.py", "tariff_scroll.py", "route_check.py", "seo_check.py"]


def up(url):
    try:
        return urllib.request.urlopen(url, timeout=3).status == 200
    except Exception:
        return False


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    base =LIVE if len(sys.argv) > 1 and sys.argv[1] == "live" else LOCAL
    server = None
    if base == LOCAL and not up(LOCAL + "/"):
        server = subprocess.Popen([sys.executable, "-m", "http.server", "8765", "--bind", "127.0.0.1"], cwd=SITE,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            if up(LOCAL + "/"):
                break
            time.sleep(0.3)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    failed = []
    try:
        for name in CHECKS:
            print(f"\n===== {name}  [{base}]", flush=True)
            r = subprocess.run([sys.executable, str(HERE / name), base], env=env, text=True, encoding="utf-8",
                               capture_output=True, timeout=600)
            print(r.stdout.strip())
            if r.returncode:
                failed.append(name)
                print(r.stderr.strip()[-2000:])
    finally:
        if server:
            server.terminate()
    print("\n===== ИТОГ:", "все проверки отработали" if not failed else "упали: " + ", ".join(failed))
    print("Смотреть в выводе: issues 0, errors [], links_bad [], route ≈ 11 км / 5 100 ₽. Скриншоты — tools/tests/_shots/")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
