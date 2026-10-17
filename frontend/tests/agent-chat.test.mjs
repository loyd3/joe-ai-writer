import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import ts from 'typescript'
async function helper() {
  const source = await fs.readFile(new URL('../src/utils/agentChat.ts', import.meta.url), 'utf8')
  return import(`data:text/javascript;base64,${Buffer.from(ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.ES2022}}).outputText).toString('base64')}`)
}
test('assistant messages hide actions and deduplicate final answer', async () => {
  const { assistantMessages } = await helper()
  assert.deepEqual(assistantMessages({messages:[{role:'user',content:'question'}, {role:'assistant',content:'先看正文。\n```json\n{"tool":"read_document"}\n```'}, {role:'assistant',content:'完成'}],answer:'完成'}), ['先看正文。','完成'])
  assert.deepEqual(assistantMessages({messages:[{role:'assistant',content:'{"tool":"read_'}],answer:''}), [])
})
test('readable preview preserves manuscript text without raw block JSON', async () => {
  const { readablePreview } = await helper()
  assert.equal(readablePreview({title:'第一章', content:[{id:'1',content:'原文'},{id:'2',content:'后文'}]}), '第一章\n\n原文\n\n后文')
})
