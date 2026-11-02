"""Real browser -> gateway -> analysis/evidence smoke test. No cloud credentials required.
Run: python tests/browser_smoke.py (install Playwright and its Chromium first).
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BID = '1088753-08-161'


def main():
    with tempfile.TemporaryDirectory() as temp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        url = f'http://127.0.0.1:{port}'
        env = {**os.environ, 'RELIEF_API_TOKEN': 'browser-test-token', 'EVIDENCE_DB_PATH': str(Path(temp)/'intake.sqlite3'),
               'AGENT_RUNTIME_RESOURCE': '', 'AGENT_RUNTIME_ID': '', 'EVIDENCE_GCS_BUCKET': '', 'BIGQUERY_MCP_MODE': 'none'}
        log = open(Path(temp)/'server.log', 'w+')
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'server.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-proxy-headers'],
                                  cwd=ROOT, env=env, stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    with urlopen(url + '/healthz', timeout=1) as response:
                        if response.status == 200: break
                except OSError:
                    if server.poll() is not None: raise RuntimeError('Gateway exited during startup')
                    time.sleep(.1)
            else: raise RuntimeError('Gateway did not become ready')
            with sync_playwright() as p:
                launch = {'headless': True}
                if os.environ.get('CHROME_EXECUTABLE'): launch['executable_path'] = os.environ['CHROME_EXECUTABLE']
                browser = p.chromium.launch(**launch)
                page = browser.new_page(viewport={'width': 1440, 'height': 1100})
                errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url)
                expect(page.locator('#error')).to_contain_text('access token')
                page.locator('.access').evaluate('(el) => el.open = true')
                page.locator('#access-token').fill('browser-test-token'); page.locator('#access-form button').click()
                expect(page.locator('#queue-body tr')).to_have_count(232)
                page.locator('#business-a').select_option(BID)
                expect(page.locator('#intake-status')).to_contain_text('MISSING')
                page.locator('#max-hops').fill('6'); page.locator('#tool-form button').click()
                expect(page.locator('#tool-output')).to_contain_text('Sour Flour')
                expect(page.locator('#trace-paths')).to_contain_text('Sour Flour')
                fields = {'cash': '12000', 'quarterly_operating_burn': '30000', 'direct_employees': '5',
                          'location_count': '1', 'institutional_ownership_pct': '0', 'requested_amount': '10000',
                          'financial_reference': 'test financial document', 'ownership_reference': 'test ownership document',
                          'notes': '<img src=x onerror="window.injected=true">'}
                for name, value in fields.items(): page.locator(f'#evidence-form [name="{name}"]').fill(value)
                page.locator('[name="storefront_certified"]').check()
                page.locator('#evidence-form button').click()
                expect(page.locator('#intake-status')).to_contain_text('PENDING_REVIEW')
                page.locator('#reviewer').fill('Browser test officer'); page.locator('#review-notes').fill('Document references inspected')
                page.locator('#review-form button').click()
                expect(page.locator('#intake-status')).to_contain_text('VERIFIED_INTAKE')
                expect(page.locator('#intake-status')).to_contain_text('0.4 quarters')
                assert page.locator('#evidence-history img').count() == 0
                assert not page.evaluate('Boolean(window.injected)')
                expect(page.locator('#report')).to_contain_text('No awards approved')
                page.locator('#mode').select_option('canonical')
                expect(page.locator('#queue-body tr')).to_have_count(11)
                page.locator('#budget').fill('5000'); page.locator('#run-analysis').click()
                expect(page.locator('#report')).to_contain_text('Budget $5,000.00')
                sour = page.locator('#queue-body tr').filter(has_text='Sour Flour')
                expect(sour.locator('td').nth(2)).to_have_text('$0.00')
                page.locator('#business-a').select_option('cm_01'); page.locator('#action').select_option('what_if')
                page.locator('#grant-amount').fill('5000'); page.locator('#tool-form button').click()
                expect(page.locator('#tool-output')).to_contain_text('"assumed_survival_lift": 0')
                with page.expect_download() as download:
                    page.locator('#download-report').click()
                assert 'Budget $5,000.00' in Path(download.value.path()).read_text()
                page.set_viewport_size({'width': 390, 'height': 844})
                screenshot = os.environ.get('BROWSER_SCREENSHOT')
                if screenshot: page.screenshot(path=screenshot, full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), page.evaluate('Array.from(document.querySelectorAll("body *")).filter(el => el.getBoundingClientRect().right > window.innerWidth).slice(0,8).map(el => [el.tagName, el.id, el.getBoundingClientRect().right])')
                page.route('**/api/agent/run', lambda route: route.fulfill(status=503, content_type='application/json', body='{"detail":"Test backend unavailable"}'))
                page.locator('#run-analysis').click()
                expect(page.locator('#error')).to_contain_text('Test backend unavailable')
                expect(page.locator('#queue-body tr')).to_have_count(0)
                expect(page.locator('#download-report')).to_be_disabled()
                assert not errors, errors
                browser.close()
                print('Browser smoke passed: authentication, source paths, saved intake, review, scenario allocation, report download, mobile layout, failure handling and safe text rendering.')
        except Exception:
            log.flush(); log.seek(0); print(log.read()[-8000:], file=sys.stderr)
            raise
        finally:
            server.terminate(); server.wait(timeout=10); log.close()


if __name__ == '__main__': main()
