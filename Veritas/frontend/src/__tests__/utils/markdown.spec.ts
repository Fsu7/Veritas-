import { describe, it, expect } from 'vitest'
import { renderMarkdown } from '@/utils/markdown'

describe('renderMarkdown', () => {
  it('renders headings', () => {
    const html = renderMarkdown('# 标题')
    expect(html).toContain('<h1>标题</h1>')
  })

  it('renders unordered lists', () => {
    const html = renderMarkdown('- 项目1\n- 项目2')
    expect(html).toContain('<ul>')
    expect(html).toContain('<li>项目1</li>')
    expect(html).toContain('<li>项目2</li>')
  })

  it('renders ordered lists', () => {
    const html = renderMarkdown('1. 第一\n2. 第二')
    expect(html).toContain('<ol>')
    expect(html).toContain('<li>第一</li>')
  })

  it('renders blockquotes', () => {
    const html = renderMarkdown('> 引用内容')
    expect(html).toContain('<blockquote>')
    expect(html).toContain('引用内容')
  })

  it('renders code blocks', () => {
    const html = renderMarkdown('```js\nconst x = 1\n```')
    expect(html).toContain('<pre>')
    expect(html).toContain('<code')
  })

  it('returns empty string for empty input', () => {
    expect(renderMarkdown('')).toBe('')
  })

  it('strips raw HTML for XSS protection', () => {
    const html = renderMarkdown('<script>alert(1)</script>')
    expect(html).not.toContain('<script>')
  })

  it('converts URLs to links when linkify is enabled', () => {
    const html = renderMarkdown('访问 https://example.com 查看')
    expect(html).toContain('href="https://example.com"')
  })
})
