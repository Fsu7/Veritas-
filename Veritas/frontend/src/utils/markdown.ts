import MarkdownIt from 'markdown-it'
import { linkifyCitations } from '@/utils/citation'
import type { Citation } from '@/types/analysis'

/**
 * Markdown 渲染实例
 * - html: false 禁用原始 HTML 防止 XSS
 * - linkify URL 自动转链接
 * - typographer 智能引号替换
 * - breaks 换行转 <br>
 */
export const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true
})

/**
 * 渲染 Markdown 文本为 HTML
 * 必须在 v-html 中使用
 */
export function renderMarkdown(text: string): string {
  if (!text) return ''
  return md.render(text)
}

/**
 * 渲染 Markdown 文本为 HTML，并将 [Author, Year] 引用转换为可点击链接
 * 用于综述编辑器的实时预览
 * @param text 原始 Markdown 文本
 * @param citations 引用列表，用于匹配 paperId
 * @returns 渲染后的 HTML 字符串
 */
export function renderMarkdownWithCitations(text: string, citations: Citation[] = []): string {
  if (!text) return ''
  const linked = linkifyCitations(text, citations)
  return md.render(linked)
}
