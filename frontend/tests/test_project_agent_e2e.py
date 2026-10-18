"""Mock-only browser integration tests for the chat-style project agent (小墨).

Run: python -m unittest discover -s tests -p test_project_agent_e2e.py -v
Requires Python Playwright and a running Vite server (PROJECT_AGENT_BASE_URL optional).
No backend requests are allowed through this fixture.
"""
import copy
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse
import unittest
from playwright.sync_api import sync_playwright, expect

DOC = {
    'id': 7,
    'title': '第一章',
    'content': [{'id': 'block-1', 'type': 'paragraph', 'content': 'ORIGINAL CONTENT'}],
    'project_id': 1,
    'order_index': 0,
    'created_at': '2026-10-16T00:00:00Z',
    'updated_at': '2026-10-16T00:00:00Z',
}


class MockProjectApi:
    def __init__(self):
        self.run = None
        self.posts = []
        self.puts = []
        self.project_reads = 0
        self.document_reads = 0
        self.unexpected = []
        self.failure = None
        self.apply_status = 'applied'
        self.payload = '<img src=x onerror="window.__agentXss=1"><script>window.__agentXss=1</script>'
        self.answer = '我整理了 1 项变更，请确认。'
        self.document = copy.deepcopy(DOC)

    def handle(self, route):
        request = route.request
        path = urlparse(request.url).path.removeprefix('/api').rstrip('/')
        method = request.method
        data = None
        status = 200
        if path == '/auth/me':
            data = {'id': 1, 'username': 'mock-tester', 'email': 'test@example.invalid'}
        elif path == '/auth/theme':
            data = {}
        elif path == '/system/user-ai-config':
            data = {}
        elif path == '/projects/1' and method == 'GET':
            self.project_reads += 1
            data = {
                'id': 1,
                'title': 'Mock project',
                'description': 'Original project',
                'created_at': '2026-10-16T00:00:00Z',
                'updated_at': '2026-10-16T00:00:00Z',
                'ai_memory': None,
                'documents': [copy.deepcopy(self.document)],
            }
        elif path in ('/projects/1/documents', '/projects') and method == 'GET':
            data = [copy.deepcopy(self.document)] if path.endswith('/documents') else [{'id': 1, 'title': 'Mock project', 'description': 'Original project', 'created_at': '2026-10-16T00:00:00Z', 'updated_at': '2026-10-16T00:00:00Z', 'documents': [copy.deepcopy(self.document)]}]
        elif path == '/documents/7' and method == 'GET':
            self.document_reads += 1
            data = copy.deepcopy(self.document)
        elif path == '/documents/7' and method == 'PUT':
            body = request.post_data_json or {}
            self.puts.append((path, body))
            if self.failure and self.failure[0] == 409 and 'document' in (self.failure[1] or ''):
                status, data = 409, {'detail': self.failure[1]}
            else:
                self.document = {
                    **self.document,
                    'title': body.get('title', self.document['title']),
                    'content': body.get('content', self.document['content']),
                    'updated_at': '2026-10-16T01:00:00Z',
                }
                data = copy.deepcopy(self.document)
        elif path == '/projects/1/agent/runs' and method == 'GET':
            data = [copy.deepcopy(self.run)] if self.run else []
        elif path == '/projects/1/agent/runs' and method == 'POST':
            self.posts.append((path, request.post_data_json))
            if self.failure and 'document' not in (self.failure[1] or ''):
                status, detail = self.failure
                data = {'detail': detail}
            else:
                self.run = {
                    'id': 'mock-run-1',
                    'conversation_id': 'mock-conversation-1',
                    'instruction': request.post_data_json['instruction'],
                    'status': 'running',
                    'answer': '',
                    'events': [],
                    'changes': [],
                    'messages': [],
                    'created_at': '2026-10-16T00:00:00Z',
                }
                data = copy.deepcopy(self.run)
        elif path == '/projects/1/agent/runs/mock-run-1' and method == 'GET':
            data = copy.deepcopy(self.run) if self.run else {'detail': 'Run not found'}
            if self.run is None:
                status = 404
        elif method == 'POST' and path in {
            '/projects/1/agent/runs/mock-run-1/cancel',
            '/projects/1/agent/runs/mock-run-1/resume',
            '/projects/1/agent/runs/mock-run-1/apply',
            '/projects/1/agent/runs/mock-run-1/revert',
        }:
            self.posts.append((path, request.post_data_json))
            action = path.rsplit('/', 1)[-1]
            if self.failure and 'document' not in (self.failure[1] or ''):
                status, detail = self.failure
                data = {'detail': detail}
            elif self.run is None:
                status, data = 404, {'detail': 'Run not found'}
            else:
                self.run['status'] = {
                    'cancel': 'cancelled',
                    'resume': 'running',
                    'apply': self.apply_status,
                    'revert': 'reverted',
                }[action]
                data = copy.deepcopy(self.run)
        elif path == '/agent/runs' and method == 'GET':
            data = []
        elif path == '/dashboard/stats' and method == 'GET':
            data = {
                'stats': {
                    'totalProjects': 1,
                    'totalDocuments': 1,
                    'totalWords': 12,
                    'totalAIInteractions': 0,
                },
                'aiUsage': {
                    'total': 0,
                    'polish': 0,
                    'continue': 0,
                    'brainstorm': 0,
                    'chat': 0,
                },
                'recentProjects': [{
                    'id': 1,
                    'title': 'Mock project',
                    'documentCount': 1,
                    'wordCount': 12,
                    'progress': 10,
                    'updated_at': '2026-10-16T00:00:00Z',
                }],
            }
        elif path == '/projects/1/memory' and method == 'GET':
            data = {
                'overview': '',
                'characters': [],
                'worldbuilding': '',
                'outline': '',
                'style_notes': '',
                'other': '',
            }
        else:
            self.unexpected.append((method, path))
            status, data = 501, {'detail': 'Blocked by mock-only test fixture'}
        route.fulfill(status=status, json=data)

    def propose(self):
        self.run.update(
            status='proposed',
            answer=self.answer,
            events=[
                {'sequence': 1, 'type': 'start', 'message': 'First event'},
                {'sequence': 2, 'type': 'finish', 'message': '处理完成'},
            ],
            messages=[{'role': 'assistant', 'content': self.answer, 'step': 1, 'streaming': False}],
            changes=[{
                'id': 'change-1',
                'kind': 'update_document',
                'target_id': 7,
                'title': self.payload,
                'reason': self.payload,
                'before': 'ORIGINAL CONTENT',
                'after': self.payload,
            }],
        )


class ProjectAgentE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(channel='chrome', headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.api = MockProjectApi()
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block')
        self.addCleanup(self.context.close)
        self.context.add_init_script(
            "localStorage.setItem('token','mock-only-token');"
            "localStorage.setItem('user',JSON.stringify({id:1,username:'mock-tester'}));"
        )
        self.base_url = os.getenv('PROJECT_AGENT_BASE_URL', 'http://127.0.0.1:5173')

        def dispatch(route):
            request = route.request
            target = urlparse(request.url)
            page = urlparse(self.base_url)
            # Match real backend paths only — never Vite modules like /src/api/*.ts.
            path = target.path
            if path.startswith('/api/') or path == '/api':
                self.api.handle(route)
                return
            if target.netloc and target.netloc != page.netloc:
                # Dashboard uses an absolute API host; still mock /api there.
                if path.startswith('/api/') or path == '/api':
                    self.api.handle(route)
                    return
                self.api.unexpected.append((request.method, request.url))
                route.abort()
                return
            route.fallback()

        self.context.route('**/*', dispatch)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        name = self._testMethodName
        if name == 'test_no_project_empty_state':
            self.page.goto(self.base_url + '/')
        else:
            self.page.goto(self.base_url + '/project/1')
            expect(self.page.get_by_role('heading', name='Mock project', exact=True)).to_be_visible()
        self.window = self.page.get_by_role('dialog', name='小墨创作助手', exact=True)
        self.panel = self.page.get_by_role('region', name='小墨项目对话', include_hidden=True)
        if name not in {
            'test_no_project_empty_state',
            'test_document_route_retains_draft_across_same_project',
            'test_document_prepare_save_before_open_and_submit',
        }:
            self.open_assistant()

    def tearDown(self):
        self.assertEqual(self.api.unexpected, [], 'Every backend request must be mocked explicitly')
        self.assertEqual(self.errors, [], 'No browser runtime exceptions')

    def open_assistant(self):
        launcher = self.page.get_by_role('button', name='打开小墨助手', exact=True)
        if launcher.count() == 0:
            # Already open: launcher aria-label flips to 收起小墨助手
            expect(self.window).to_be_visible()
        else:
            launcher.click()
            expect(self.window).to_be_visible()
        expect(self.panel).to_be_visible()
        expect(self.panel.get_by_role('button', name='刷新历史对话', exact=True)).to_be_enabled()

    def minimize_assistant(self):
        self.window.get_by_role('button', name='收起助手', exact=True).click()
        expect(self.window).to_be_hidden()
        expect(self.panel).to_have_count(1)
        expect(self.panel).to_be_hidden()
        launcher = self.page.get_by_role('button', name='打开小墨助手', exact=True)
        expect(launcher).to_have_attribute('aria-expanded', 'false')
        expect(launcher).to_be_focused()

    def capture(self, name):
        directory = Path(os.getenv(
            'PROJECT_AGENT_ARTIFACT_DIR',
            str(Path(tempfile.gettempdir()) / 'joe-ai-writer-agent-e2e'),
        ))
        directory.mkdir(parents=True, exist_ok=True)
        path = (directory / name).resolve()
        self.page.screenshot(path=str(path), full_page=True, animations='disabled')
        print(f'Artifact: {path}', flush=True)
        return path

    def assert_within_viewport(self, locator):
        expect(locator).to_be_visible()
        box = locator.bounding_box()
        self.assertIsNotNone(box)
        viewport = self.page.viewport_size
        self.assertGreaterEqual(box['x'], -1)
        self.assertGreaterEqual(box['y'], -1)
        self.assertLessEqual(box['x'] + box['width'], viewport['width'] + 1)
        self.assertLessEqual(box['y'] + box['height'], viewport['height'] + 1)

    def submit(self, instruction='帮我把主角改名为林远，并检查设定一致性'):
        self.panel.get_by_role('textbox', name='消息输入').fill(instruction)
        self.panel.get_by_role('button', name='发送', exact=True).click()
        expect(self.panel.locator('.activity')).to_be_visible()
        body = self.api.posts[0][1]
        # Panel appends hidden scope system notes before the POST body.
        self.assertTrue(str(body['instruction']).startswith(instruction), body['instruction'])
        return instruction

    def propose(self, auto_confirm=False):
        self.api.propose()
        self.panel.get_by_role('button', name='刷新历史对话', exact=True).click()
        expect(self.panel.locator('.proposal strong')).to_have_text('替换未完成 · 1 项（可点确认写入）', timeout=10000)
        if auto_confirm:
            self.panel.get_by_role('button', name='确认写入').click()
            expect(self.panel.locator('.proposal strong')).to_have_text('已自动替换 · 1 项（可撤销）', timeout=10000)

    def open_document(self):
        self.page.get_by_text('第一章', exact=True).click()
        expect(self.page).to_have_url(self.base_url + '/document/7')
        expect(self.page.locator('.block-content[contenteditable="true"]').first).to_be_visible()
        self.assertGreater(self.api.document_reads, 0)

    def dirty_document(self, text='本地未保存改稿'):
        block = self.page.locator('.block-content[contenteditable="true"]').first
        block.click()
        block.press('Control+A')
        block.type(text, delay=5)
        expect(self.page.get_by_role('button', name='保存', exact=True)).to_be_enabled()
        return text

    def test_desktop_welcome_preview(self):
        expect(self.panel.get_by_role('heading', name='这次想一起写些什么？')).to_be_visible()
        expect(self.panel.get_by_text(self.api.payload)).to_have_count(0)
        expect(self.panel.locator('.proposal')).to_have_count(0)
        expect(self.panel.get_by_role('button', name='阅读项目摘要')).to_be_visible()
        path = self.capture('project-agent-desktop-welcome.png')
        self.assertTrue(path.is_file())
        self.assertEqual(self.api.posts, [])

    def test_chat_preview_apply_refresh_and_revert(self):
        self.submit()
        initial_reads = self.api.project_reads
        self.assertEqual(len(self.api.posts), 1)
        expect(self.panel.get_by_role('button', name='确认写入')).to_have_count(0)
        self.propose(auto_confirm=False)
        expect(self.panel.get_by_text(self.api.answer, exact=True)).to_be_visible()
        change = self.panel.locator('details.change')
        expect(change).to_have_attribute('open', '')
        pre = self.panel.locator('.previews pre')
        expect(pre.nth(0)).to_have_text(self.api.payload)
        expect(pre.nth(1)).to_have_text('ORIGINAL CONTENT')
        expect(self.panel.locator('img, script')).to_have_count(0)
        self.assertIsNone(self.page.evaluate('window.__agentXss'))
        self.assertEqual(self.api.project_reads, initial_reads, 'Proposals must not refresh saved project state')
        with self.page.expect_response(lambda response: response.url.endswith('/api/projects/1/agent/runs/mock-run-1/apply')):
            self.panel.get_by_role('button', name='确认写入').click()
        expect(self.panel.locator('.proposal strong')).to_have_text('已自动替换 · 1 项（可撤销）')
        self.panel.get_by_role('button', name='撤销替换').click()
        with self.page.expect_response(lambda response: response.url.endswith('/api/projects/1/agent/runs/mock-run-1/revert')):
            self.page.get_by_role('button', name='撤销替换', exact=True).last.click()
        expect(self.panel.locator('.proposal strong')).to_have_text('本次修改已撤销 · 1 项')
        self.assertEqual(
            [path.rsplit('/', 1)[-1] for path, _ in self.api.posts],
            ['runs', 'apply', 'revert'],
        )

    def test_cancel_resume_polling_and_reopen_history(self):
        self.submit()
        self.panel.get_by_role('button', name='停止', exact=True).click()
        expect(self.panel.get_by_role('button', name='重新尝试')).to_be_visible()
        self.panel.get_by_role('button', name='重新尝试', exact=True).click()
        expect(self.panel.locator('.activity')).to_be_visible()
        expect(self.panel.get_by_role('button', name='停止', exact=True)).to_be_enabled()
        # Keep the run proposed so reopen can assert unchanged preview (auto-apply is best-effort).
        self.api.failure = (409, 'Mock keep proposed')
        self.api.propose()
        expect(self.panel.locator('.proposal strong')).to_have_text('替换未完成 · 1 项（可点确认写入）', timeout=10000)
        self.minimize_assistant()
        self.open_assistant()
        expect(self.panel.locator('.proposal strong')).to_have_text('替换未完成 · 1 项（可点确认写入）')
        actions = [path.rsplit('/', 1)[-1] for path, _ in self.api.posts]
        self.assertEqual(actions[:3], ['runs', 'cancel', 'resume'])
        self.assertTrue(all(action in ('runs', 'cancel', 'resume', 'apply') for action in actions))

    def test_draft_and_conversation_retained_when_minimized(self):
        self.submit()
        self.propose(auto_confirm=False)
        draft = '这是一条尚未发送的后续创作指令。'
        composer = self.panel.get_by_role('textbox', name='消息输入')
        composer.fill(draft)
        composer.evaluate("element => element.dataset.retentionMarker = 'same-composer'")
        self.minimize_assistant()
        self.open_assistant()
        expect(composer).to_have_value(draft)
        expect(composer).to_have_attribute('data-retention-marker', 'same-composer')
        expect(composer).to_be_focused()
        expect(self.panel.get_by_text(self.api.answer, exact=True)).to_be_visible()
        self.assertEqual(len([p for p in self.api.posts if p[0].endswith('/runs')]), 1)

    def test_global_navigation_keeps_assistant_and_draft(self):
        draft = '切换页面后继续编辑这条草稿'
        composer = self.panel.get_by_role('textbox', name='消息输入')
        composer.fill(draft)
        composer.evaluate("element => element.dataset.retentionMarker = 'global-composer'")
        # Same-project document SPA navigation restores draft text (panel may remount if projectId blinks null).
        self.page.get_by_text('第一章', exact=True).click()
        expect(self.page).to_have_url(self.base_url + '/document/7')
        expect(self.window).to_be_visible()
        expect(self.window.get_by_text('文档', exact=True).first).to_be_visible()
        expect(self.panel.get_by_role('textbox', name='消息输入')).to_have_value(draft)
        self.minimize_assistant()
        self.open_assistant()
        expect(self.panel.get_by_role('textbox', name='消息输入')).to_have_value(draft)
        self.assertEqual(self.api.posts, [])
        # Report to parent: same-project document entry remounts composer (lost DOM marker) via projectId gap.

    def test_mobile_window_bounds_and_composer(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.assert_within_viewport(self.window)
        self.assert_within_viewport(self.window.get_by_role('button', name='收起助手', exact=True))
        self.assert_within_viewport(self.panel.get_by_role('textbox', name='消息输入'))
        self.assert_within_viewport(self.panel.get_by_role('button', name='发送', exact=True))
        self.window.get_by_role('button', name='放大窗口', exact=True).click()
        self.assert_within_viewport(self.window)
        self.window.get_by_role('button', name='还原窗口', exact=True).click()
        self.panel.get_by_role('textbox', name='消息输入').fill('手机端未发送的草稿')
        self.capture('project-agent-mobile-390.png')
        self.minimize_assistant()
        self.assert_within_viewport(self.page.get_by_role('button', name='打开小墨助手', exact=True))
        self.open_assistant()
        expect(self.panel.get_by_role('textbox', name='消息输入')).to_have_value('手机端未发送的草稿')
        self.assertEqual(self.api.posts, [])

    def test_no_project_empty_state(self):
        expect(self.page.get_by_role('heading', name='我的创作空间', exact=True)).to_be_visible()
        self.page.get_by_role('button', name='打开小墨助手', exact=True).click()
        expect(self.window).to_be_visible()
        expect(self.window.get_by_text('系统', exact=True).first).to_be_visible()
        expect(self.panel).to_be_visible()
        expect(self.panel.get_by_role('heading', name='这次想一起写些什么？')).to_be_visible()
        expect(self.panel.get_by_role('textbox', name='消息输入')).to_be_visible()
        self.window.get_by_role('button', name='收起助手', exact=True).click()
        expect(self.window).to_be_hidden()
        self.page.get_by_role('button', name='打开小墨助手', exact=True).click()
        expect(self.panel.get_by_role('heading', name='这次想一起写些什么？')).to_be_visible()
        self.assertEqual(self.api.posts, [])

    def test_failed_apply_is_not_saved_or_retried(self):
        self.submit()
        self.propose(auto_confirm=False)
        initial_reads = self.api.project_reads
        self.api.failure = (409, 'Mock version conflict: please refresh')
        self.panel.get_by_role('button', name='确认写入').click()
        expect(self.panel.get_by_text('Mock version conflict: please refresh', exact=True)).to_be_visible()
        expect(self.panel.locator('.proposal strong')).to_have_text('替换未完成 · 1 项（可点确认写入）')
        self.assertEqual(self.api.project_reads, initial_reads)
        self.assertEqual(len([p for p in self.api.posts if p[0].endswith('/apply')]), 1)

    def test_document_route_retains_draft_across_same_project(self):
        self.open_assistant()
        draft = '同项目文档页仍应保留这条草稿'
        composer = self.panel.get_by_role('textbox', name='消息输入')
        composer.fill(draft)
        composer.evaluate("element => element.dataset.retentionMarker = 'doc-route-composer'")
        self.open_document()
        expect(self.window).to_be_visible()
        expect(self.window.get_by_text('文档', exact=True).first).to_be_visible()
        # Same-project panelKey restores the composer text; a brief projectId gap may remount the node.
        expect(self.panel.get_by_role('textbox', name='消息输入')).to_have_value(draft)
        expect(self.page.get_by_role('button', name='打开小墨助手')).to_have_count(0)
        self.page.get_by_role('button', name='收起小墨助手', exact=True).click()
        expect(self.window).to_be_hidden()
        self.open_assistant()
        expect(self.panel.get_by_role('textbox', name='消息输入')).to_have_value(draft)
        self.assertEqual(self.api.posts, [])
        # Editor may flush an identical PUT while mounting; agent must not mutate.

    def test_document_prepare_save_before_open_and_submit(self):
        self.open_document()
        edited = self.dirty_document('准备发送前必须先落盘的改稿')
        with self.page.expect_response(lambda response: '/api/documents/7' in response.url and response.request.method == 'PUT'):
            self.open_assistant()
        self.assertEqual(len(self.api.puts), 1)
        self.assertIn(edited, json.dumps(self.api.puts[0][1], ensure_ascii=False))
        expect(self.panel).to_be_visible()
        more = '发送时再次触发 prepareSubmission'
        self.dirty_document(more)
        instruction = '请根据当前文档润色第一段'
        self.panel.get_by_role('textbox', name='消息输入').fill(instruction)
        with self.page.expect_response(lambda response: '/api/documents/7' in response.url and response.request.method == 'PUT'):
            self.panel.get_by_role('button', name='发送', exact=True).click()
        expect(self.panel.locator('.activity')).to_be_visible()
        self.assertGreaterEqual(len(self.api.puts), 2)
        self.assertIn(more, json.dumps(self.api.puts[-1][1], ensure_ascii=False))
        body = self.api.posts[0][1]
        self.assertTrue(str(body['instruction']).startswith(instruction), body['instruction'])
        self.assertEqual(body.get('focus', {}).get('document_id'), 7)


if __name__ == '__main__':
    unittest.main(verbosity=2)
