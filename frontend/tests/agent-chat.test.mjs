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
test('assistant turn splits thinking from final', async () => {
  const { assistantTurnDisplay, thinkingSummary } = await helper()
  assert.deepEqual(
    assistantTurnDisplay({
      messages: [
        { role: 'assistant', content: '我先读选中段。' },
        { role: 'assistant', content: '开始扩写。' },
        { role: 'assistant', content: '已扩写完成。' },
      ],
      answer: '已扩写完成。',
    }),
    { thinking: ['我先读选中段。', '开始扩写。'], final: '已扩写完成。' },
  )
  assert.match(thinkingSummary(['我先读选中段。', '开始扩写。']), /共 2 步/)
})
test('strip system notes from user instruction', async () => {
  const { stripAgentSystemNotes, extractAgentSystemNotes, mergeAgentSystemNotes } = await helper()
  const full =
    '请扩写选中段落\n\n（系统：当前打开的文档就是 document_id=12。禁止列举。）\n\n（系统：用户已选中 3 个段落，目标已锁定：block_id=a。）'
  assert.equal(stripAgentSystemNotes(full), '请扩写选中段落')
  const { visible, system } = extractAgentSystemNotes(full)
  assert.equal(visible, '请扩写选中段落')
  assert.match(system, /document_id=12/)
  assert.match(system, /block_id=a/)
  assert.match(mergeAgentSystemNotes(visible, system), /document_id=12/)
  assert.match(mergeAgentSystemNotes('请帮我做脑洞写作。', '（系统：先 list_brainstorm_ideas。）'), /list_brainstorm_ideas/)
})
test('readable preview preserves manuscript text without raw block JSON', async () => {
  const { readablePreview } = await helper()
  assert.equal(readablePreview({title:'第一章', content:[{id:'1',content:'原文'},{id:'2',content:'后文'}]}), '第一章\n\n原文\n\n后文')
})
