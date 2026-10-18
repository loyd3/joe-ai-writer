import assert from 'node:assert/strict'
import test from 'node:test'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { transformSync } from 'esbuild'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(import.meta.url)

function loadIntent() {
  const source = require('fs').readFileSync(join(root, 'src/utils/xiaoMoIntent.ts'), 'utf8')
  const { code } = transformSync(source, { loader: 'ts', format: 'cjs' })
  const module = { exports: {} }
  // eslint-disable-next-line no-new-func
  Function('exports', 'module', 'require', code)(module.exports, module, require)
  return module.exports
}

test('document page always prefers agent', () => {
  const { resolveXiaoMoIntent } = loadIntent()
  assert.equal(resolveXiaoMoIntent('润色这段', { inDocument: true }), 'agent')
  assert.equal(resolveXiaoMoIntent('写得更顺一点', { inDocument: true, hasAttachment: true }), 'agent')
  assert.equal(resolveXiaoMoIntent('你好', { inDocument: true }), 'agent')
})

test('actionToInstruction returns natural edit prompts', () => {
  const { actionToInstruction } = loadIntent()
  assert.match(actionToInstruction('polish'), /润色/)
  assert.match(actionToInstruction('expand'), /扩写/)
})

test('documentToolInstruction covers former AI tool menu', () => {
  const { documentToolInstruction, DOCUMENT_AI_SHORTCUTS } = loadIntent()
  assert.equal(DOCUMENT_AI_SHORTCUTS.length, 6)
  const gen = documentToolInstruction('generate', 12)
  assert.match(gen, /续写|生成/)
  assert.match(gen, /（系统：/)
  assert.match(gen, /document_id=12/)
  assert.match(gen, /read_memory/)
  assert.match(documentToolInstruction('rewrite_settings', 3), /设定/)
  assert.match(documentToolInstruction('extract', 3), /扩展/)
  assert.match(documentToolInstruction('video_script', 3), /propose_create_document/)
  assert.match(documentToolInstruction('film_script', 3), /影视/)
  assert.match(documentToolInstruction('format_style', 3), /排版/)
})

test('writingToolInstruction covers project writing shortcuts', () => {
  const { writingToolInstruction, PROJECT_WRITING_SHORTCUTS } = loadIntent()
  assert.equal(PROJECT_WRITING_SHORTCUTS.length, 4)
  const brain = writingToolInstruction('brainstorm', 7, 3)
  assert.match(brain, /脑洞写作/)
  assert.match(brain, /（系统：/)
  assert.match(brain, /list_brainstorm_ideas/)
  assert.match(brain, /project_id=7/)
  assert.match(brain, /document_id=3/)
  assert.match(writingToolInstruction('hot_topics', 7), /list_hot_topics/)
  assert.match(writingToolInstruction('copywriting', 7), /copywriting_write/)
  assert.match(writingToolInstruction('story', 7), /propose_story_settings/)
  const noProject = writingToolInstruction('brainstorm', null)
  assert.match(noProject, /create_project/)
  assert.match(noProject, /智能创建项目|无项目/)
})
