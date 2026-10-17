import type { Block, DocumentUpdate } from '@/api/types'

export interface EditorSaveSnapshot {
  documentId: number
  payload: DocumentUpdate
}

/** Freeze the exact editor state sent to the server, not reactive references. */
export function captureEditorSave(
  documentId: number,
  title: string,
  content: Block[],
  expectedUpdatedAt: string,
): EditorSaveSnapshot {
  return {
    documentId,
    payload: {
      title,
      content: JSON.parse(JSON.stringify(content)) as Block[],
      expected_updated_at: expectedUpdatedAt,
    },
  }
}

export function matchesEditorSave(
  snapshot: EditorSaveSnapshot,
  documentId: number,
  title: string,
  content: Block[],
): boolean {
  return snapshot.documentId === documentId
    && snapshot.payload.title === title
    && JSON.stringify(snapshot.payload.content) === JSON.stringify(content)
}
