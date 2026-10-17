"""Mock-only browser integration tests for the chat-style project agent (小墨).

Run: python -m unittest discover -s tests -p test_project_agent_e2e.py -v
Requires Python Playwright and a running Vite server (PROJECT_AGENT_BASE_URL optional).
No backend requests are allowed through this fixture.
"""
import copy
import os
import re
import tempfile
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright, expect

# 只拦截真正的后端 API（/api/<segment>），不能误伤 Vite 提供的 /src/api/*.ts 源码模块
API_ROUTE = re.compile(r'.*/api/(?![^/?]*\.).*')


class MockProjectApi:
    def __init__(self):
        self.run = None
        self.posts = []
        self.project_reads = 0
        self.unexpected = []
        self.failure = None
        self.apply_status = 'applied'
        self.payload = '<img src=x onerror="window.__agentXss=1"><script>window.__agentXss=1</script>'
        self.answer = '我整理了 1 项变更，请确认。'

    def handle(self, route):
        request = route.request
        from urllib.parse import urlparse
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
            data = {'id': 1, 'title': 'Mock project', 'description': 'Original project', 'created_at': '2026-10-16T00:00:00Z', 'updated_at': '2026-10-16T00:00:00Z', 'ai_memory': None, 'documents': []}
        elif path in ('/projects/1/documents', '/projects') and method == 'GET':
            data = []
        elif path.startswith('/projects/1/agent/runs'):
            if method == 'POST':
                self.posts.append((path, request.post_data_json))
                if self.failure:
                    status, detail = self.failure
                    data = {'detail': detail}
                elif path.endswith('/runs'):
                    self.run = {'id': 'mock-run-1', 'conversation_id': 'mock-conversation-1', 'instruction': request.post_data_json['instruction'], 'status': 'running', 'answer': '', 'events': [], 'changes': [], 'messages': [], 'created_at': '2026-10-16T00:00:00Z'}
                else:
                    action = path.rsplit('/', 1)[-1]
                    self.run['status'] = {'cancel': 'cancelled', 'resume': 'running', 'apply': self.apply_status, 'revert': 'reverted'}[action]
                if data is None:
                    data = copy.deepcopy(self.run)
            else:
                data = [copy.deepcopy(self.run)] if path.endswith('/runs') and self.run else ([] if path.endswith('/runs') else copy.deepcopy(self.run))
        else:
            self.unexpected.append((method, path))
            status, data = 501, {'detail': 'Blocked by mock-only test fixture'}
        route.fulfill(status=status, json=data)

    def propose(self):
        self.run.update(status='proposed', answer=self.answer,
                        events=[{'sequence': 1, 'type': 'start', 'message': 'First event'},
                                {'sequence': 2, 'type': 'finish', 'message': '处理完成'}],
                        messages=[{'role': 'assistant', 'content': self.answer, 'step': 1, 'streaming': False}],
                        changes=[{'id': 'change-1', 'kind': 'update_document', 'target_id': 7, 'title': self.payload, 'reason': self.payload, 'before': 'ORIGINAL CONTENT', 'after': self.payload}])


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
        self.context.add_init_script("localStorage.setItem('token','mock-only-token'); localStorage.setItem('user',JSON.stringify({id:1,username:'mock-tester'}));")
        self.context.route(API_ROUTE, self.api.handle)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.base_url = os.getenv('PROJECT_AGENT_BASE_URL', 'http://127.0.0.1:5173')
        no_project = self._testMethodName == 'test_no_project_empty_state'
        self.page.goto(self.base_url + ('/' if no_project else '/project/1'))
        self.window = self.page.get_by_role('dialog', name='小墨创作助手', exact=True)
        self.panel = self.page.get_by_role('region', name='小墨项目对话', include_hidden=True)
        if not no_project:
            # Project loading gates the global assistant's context; do not race it.
            expect(self.page.get_by_role('heading', name='Mock project', exact=True)).to_be_visible()
            self.open_assistant()

    def tearDown(self):
        self.assertEqual(self.api.unexpected, [], 'Every backend request must be mocked explicitly')
        self.assertEqual(self.errors, [], 'No browser runtime exceptions')

    def open_assistant(self):
        self.page.get_by_role('button', name='打开小墨助手', exact=True).click()
        expect(self.window).to_be_visible()
        expect(self.panel).to_be_visible()
        expect(self.panel.get_by_role('button', name='刷新历史对话', exact=True)).to_be_enabled()

    def minimize_assistant(self):
        self.window.get_by_role('button', name='收起助手', exact=True).click()
        expect(self.window).to_be_hidden()
        # v-show must retain the mounted chat, not merely reconstruct history.
        expect(self.panel).to_have_count(1)
        expect(self.panel).to_be_hidden()
        launcher = self.page.get_by_role('button', name='打开小墨助手', exact=True)
        expect(launcher).to_have_attribute('aria-expanded', 'false')
        expect(launcher).to_be_focused()

    def capture(self, name):
        directory = Path(os.getenv('PROJECT_AGENT_ARTIFACT_DIR', str(Path(tempfile.gettempdir()) / 'joe-ai-writer-agent-e2e')))
        directory.mkdir(parents=True, exist_ok=True)
        path = (directory / name).resolve()
        self.page.screenshot(path=str(path), full_page=True, animations='disabled')
        print(f'Artifact: {path}', flush=True)

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
        self.assertEqual(self.api.posts[0][1], {'instruction': instruction})
        return instruction

    def propose(self):
        self.api.propose()
        self.panel.get_by_role('button', name='刷新历史对话', exact=True).click()
        expect(self.panel.locator('.proposal strong')).to_have_text('修改预览（尚未保存） · 1 项')

    def test_chat_preview_apply_refresh_and_revert(self):
        self.submit()
        initial_reads = self.api.project_reads
        self.assertEqual(len(self.api.posts), 1)
        expect(self.panel.get_by_role('button', name='确认修改并保存')).to_have_count(0)
        self.propose()
        # 对话气泡（assistant 答复）
        expect(self.panel.get_by_text(self.api.answer, exact=True)).to_be_visible()
        change = self.panel.locator('details.change')
        expect(change).not_to_have_attribute('open', '')
        change.locator('summary').click()
        expect(change).to_have_attribute('open', '')
        self.panel.locator('details.process summary').click()
        pre = self.panel.locator('.previews pre')
        expect(pre.nth(0)).to_have_text('ORIGINAL CONTENT')
        expect(pre.nth(1)).to_have_text(self.api.payload)
        expect(self.panel.locator('.events li').first).to_contain_text('First event')
        self.assertEqual(self.api.project_reads, initial_reads, 'Proposals must not refresh saved project state')
        self.assertEqual(len(self.api.posts), 1, 'No mutation before explicit approval')
        expect(self.panel.locator('img, script')).to_have_count(0)
        self.assertIsNone(self.page.evaluate('window.__agentXss'))
        apply = self.panel.get_by_role('button', name='确认修改并保存')
        apply.click()
        self.page.get_by_role('button', name='返回预览', exact=True).click()
        expect(apply).to_be_enabled()
        self.assertEqual(len(self.api.posts), 1, 'Dismissed confirmation must not call apply')
        apply.click()
        with self.page.expect_response(lambda response: response.url.endswith('/api/projects/1')):
            self.page.get_by_role('button', name='批准全部并保存', exact=True).click()
        expect(self.panel.locator('.proposal strong')).to_have_text('已保存到项目 · 1 项')
        self.assertGreater(self.api.project_reads, initial_reads, 'changed event must reload project')
        reads_after_apply = self.api.project_reads
        self.panel.get_by_role('button', name='撤销这次修改').click()
        with self.page.expect_response(lambda response: response.url.endswith('/api/projects/1')):
            self.page.get_by_role('button', name='确认撤销', exact=True).click()
        expect(self.panel.locator('.proposal strong')).to_have_text('本次修改已撤销 · 1 项')
        self.assertGreater(self.api.project_reads, reads_after_apply)
        self.assertEqual([path.rsplit('/', 1)[-1] for path, _ in self.api.posts], ['runs', 'apply', 'revert'])

    def test_cancel_resume_polling_and_reopen_history(self):
        self.submit()
        self.panel.get_by_role('button', name='停止', exact=True).click()
        expect(self.panel.get_by_role('button', name='重新尝试')).to_be_visible()
        self.panel.get_by_role('button', name='重新尝试', exact=True).click()
        # Wait for resume's response before advancing the mock worker state.
        expect(self.panel.locator('.activity')).to_be_visible()
        expect(self.panel.get_by_role('button', name='停止', exact=True)).to_be_enabled()
        self.api.propose()
        expect(self.panel.locator('.proposal strong')).to_have_text('修改预览（尚未保存） · 1 项', timeout=10000)
        # Minimize the floating window without destroying its chat state.
        self.minimize_assistant()
        self.open_assistant()
        expect(self.panel.locator('.proposal strong')).to_have_text('修改预览（尚未保存） · 1 项')
        self.assertEqual([path.rsplit('/', 1)[-1] for path, _ in self.api.posts], ['runs', 'cancel', 'resume'])

    def test_draft_and_conversation_retained_when_minimized(self):
        self.submit()
        self.propose()
        draft = '这是一条尚未发送的后续创作指令。'
        composer = self.panel.get_by_role('textbox', name='消息输入')
        composer.fill(draft)
        # A marker proves the same DOM node survives v-show, not just a remount.
        composer.evaluate("element => element.dataset.retentionMarker = 'same-composer'")
        self.minimize_assistant()
        self.open_assistant()
        expect(composer).to_have_value(draft)
        expect(composer).to_have_attribute('data-retention-marker', 'same-composer')
        expect(composer).to_be_focused()
        expect(self.panel.get_by_text(self.api.answer, exact=True)).to_be_visible()
        self.assertEqual(len(self.api.posts), 1, 'Reopening must not send the draft')
        self.capture('project-agent-desktop.png')

    def test_global_navigation_keeps_assistant_and_draft(self):
        draft = '切换页面后继续编辑这条草稿'
        composer = self.panel.get_by_role('textbox', name='消息输入')
        composer.fill(draft)
        composer.evaluate("element => element.dataset.retentionMarker = 'global-composer'")
        # SPA navigation must keep MainLayout and the global chat mounted.
        self.page.locator('.nav-menu .nav-item').filter(has_text='我的项目').click()
        expect(self.page).to_have_url(self.base_url + '/')
        expect(self.page.get_by_role('heading', name='我的创作空间', exact=True)).to_be_visible()
        expect(self.window).to_be_visible()
        expect(composer).to_have_value(draft)
        expect(composer).to_have_attribute('data-retention-marker', 'global-composer')
        self.minimize_assistant()
        self.open_assistant()
        expect(composer).to_have_value(draft)
        self.assertEqual(self.api.posts, [])

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
        # Full navigation starts a fresh store: no prior project context exists.
        self.page.goto(self.base_url + '/')
        expect(self.page.get_by_role('heading', name='我的创作空间', exact=True)).to_be_visible()
        self.page.get_by_role('button', name='打开小墨助手', exact=True).click()
        expect(self.window).to_be_visible()
        expect(self.window.get_by_role('heading', name='从一个项目开始创作')).to_be_visible()
        expect(self.panel).to_have_count(0)
        expect(self.window.get_by_role('textbox', name='消息输入')).to_have_count(0)
        self.window.get_by_role('button', name='前往我的项目', exact=True).click()
        expect(self.page).to_have_url(self.base_url + '/')
        self.window.get_by_role('button', name='收起助手', exact=True).click()
        expect(self.window).to_be_hidden()
        self.page.get_by_role('button', name='打开小墨助手', exact=True).click()
        expect(self.window.get_by_role('heading', name='从一个项目开始创作')).to_be_visible()
        self.assertEqual(self.api.posts, [])

    def test_failed_apply_is_not_saved_or_retried(self):
        self.submit()
        self.propose()
        initial_reads = self.api.project_reads
        self.api.failure = (409, 'Mock version conflict: please refresh')
        self.panel.get_by_role('button', name='确认修改并保存').click()
        self.page.get_by_role('button', name='批准全部并保存', exact=True).click()
        expect(self.panel.get_by_text('Mock version conflict: please refresh', exact=True)).to_be_visible()
        expect(self.panel.locator('.proposal strong')).to_have_text('修改预览（尚未保存） · 1 项')
        expect(self.panel.locator('.proposal strong')).to_have_count(1)
        self.assertEqual(self.api.project_reads, initial_reads)
        self.assertEqual(len(self.api.posts), 2, 'Mutations must not auto-retry')


if __name__ == '__main__':
    unittest.main(verbosity=2)
