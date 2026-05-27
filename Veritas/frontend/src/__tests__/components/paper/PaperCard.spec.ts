import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PaperCard from '@/components/paper/PaperCard.vue'
import type { Paper } from '@/types/paper'

const mockPaper: Paper = {
  paperId: 'p1',
  title: 'Multi-Agent Systems Survey',
  authors: ['Zhang', 'Li', 'Wang'],
  abstract: 'A comprehensive survey of multi-agent systems and their applications in collaborative decision making. This paper reviews the state of the art and identifies key challenges for future research directions.',
  year: 2024,
  venue: 'ACL',
  keywords: ['Multi-Agent', 'LLM', 'Survey'],
  citationCount: 156,
  score: 0.95,
  recommendReason: 'Highly relevant to your research'
}

describe('PaperCard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders paper title', () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper } })
    expect(wrapper.text()).toContain('Multi-Agent Systems Survey')
  })

  it('renders authors joined by comma', () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper } })
    expect(wrapper.text()).toContain('Zhang, Li, Wang')
  })

  it('renders meta with year and venue separated by dot', () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper } })
    expect(wrapper.text()).toContain('2024')
    expect(wrapper.text()).toContain('ACL')
  })

  it('renders truncated abstract', () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper } })
    expect(wrapper.text()).toContain('A comprehensive survey')
  })

  it('renders up to 3 keyword tags', () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper } })
    const tags = wrapper.findAll('.el-tag')
    expect(tags.length).toBeGreaterThanOrEqual(3)
  })

  it('renders score as percentage', () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper } })
    expect(wrapper.text()).toContain('相关度 95%')
  })

  it('renders recommend reason', () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper } })
    expect(wrapper.text()).toContain('推荐理由')
    expect(wrapper.text()).toContain('Highly relevant to your research')
  })

  it('does not render keywords section when empty', () => {
    const paper: Paper = { ...mockPaper, keywords: undefined }
    const wrapper = mount(PaperCard, { props: { paper } })
    expect(wrapper.find('.paper-card__keywords').exists()).toBe(false)
  })

  it('does not render score when undefined', () => {
    const paper: Paper = { ...mockPaper, score: undefined }
    const wrapper = mount(PaperCard, { props: { paper } })
    expect(wrapper.text()).not.toContain('相关度')
  })

  it('does not render recommend reason when undefined', () => {
    const paper: Paper = { ...mockPaper, recommendReason: undefined }
    const wrapper = mount(PaperCard, { props: { paper } })
    expect(wrapper.text()).not.toContain('推荐理由')
  })

  it('emits select event when title is clicked', async () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper } })
    await wrapper.find('.paper-card__title').trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0]).toEqual(['p1'])
  })

  it('emits analyze event when analyze button is clicked', async () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper } })
    const buttons = wrapper.findAllComponents({ name: 'ElButton' })
    const analyzeBtn = buttons.find(b => b.text() === '分析')
    await analyzeBtn?.trigger('click')
    expect(wrapper.emitted('analyze')).toBeTruthy()
    expect(wrapper.emitted('analyze')![0]).toEqual(['p1'])
  })

  it('emits favorite event when favorite button is clicked', async () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper } })
    const buttons = wrapper.findAllComponents({ name: 'ElButton' })
    const favBtn = buttons.find(b => b.text() === '收藏')
    await favBtn?.trigger('click')
    expect(wrapper.emitted('favorite')).toBeTruthy()
    expect(wrapper.emitted('favorite')![0]).toEqual(['p1'])
  })

  it('shows "已收藏" when isFavorited is true', () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper, isFavorited: true } })
    expect(wrapper.text()).toContain('已收藏')
  })

  it('shows "收藏" when isFavorited is false', () => {
    const wrapper = mount(PaperCard, { props: { paper: mockPaper, isFavorited: false } })
    expect(wrapper.text()).toContain('收藏')
  })

  it('truncates abstract over 200 characters', () => {
    const longAbstract = 'A'.repeat(300)
    const paper: Paper = { ...mockPaper, abstract: longAbstract }
    const wrapper = mount(PaperCard, { props: { paper } })
    const abstractEl = wrapper.find('.paper-card__abstract')
    expect(abstractEl.text().endsWith('...')).toBe(true)
    expect(abstractEl.text().length).toBeLessThanOrEqual(203)
  })
})
