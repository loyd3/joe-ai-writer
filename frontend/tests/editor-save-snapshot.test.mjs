import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import ts from 'typescript'

async function loadHelper() {
  const source = await fs.readFile(new URL('../src/utils/editorSaveSnapshot.ts', import.meta.url), 'utf8')
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022 } }).outputText
  return import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)
}

test('save snapshots isolate in-flight payload from subsequent edits', async () => {
  const { captureEditorSave, matchesEditorSave } = await loadHelper()
  const content = [{ id: 'b1', type: 'paragraph', content: '旧稿', props: { align: 'left' } }]
  const snapshot = captureEditorSave(12, '章节', content, '2026-10-16T01:00:00')
  content[0].content = '新稿'
  content[0].props.align = 'right'
  assert.equal(snapshot.payload.content[0].content, '旧稿')
  assert.equal(snapshot.payload.content[0].props.align, 'left')
  assert.equal(snapshot.payload.expected_updated_at, '2026-10-16T01:00:00')
  assert.equal(matchesEditorSave(snapshot, 12, '章节', content), false)
})

test('only identical document and content may be marked saved', async () => {
  const { captureEditorSave, matchesEditorSave } = await loadHelper()
  const content = [{ id: 'b1', type: 'paragraph', content: '原稿' }]
  const snapshot = captureEditorSave(12, '章节', content, 'base')
  assert.equal(matchesEditorSave(snapshot, 12, '章节', structuredClone(content)), true)
  assert.equal(matchesEditorSave(snapshot, 13, '章节', content), false)
  assert.equal(matchesEditorSave(snapshot, 12, '新标题', content), false)
})
