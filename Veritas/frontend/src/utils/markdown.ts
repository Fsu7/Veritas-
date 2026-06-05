import MarkdownIt from 'markdown-it'

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
