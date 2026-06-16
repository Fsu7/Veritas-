/**
 * CitationLink 组件测试
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import type { CitationPopupData } from '@/utils/citation'

// ============ Mock ============

vi.mock('element-plus', () => ({
  ElDialog: {
    name: 'ElDialog',
    props: ['modelValue', 'title', 'width', 'destroyOnClose'],
    emits: ['update:modelValue'],
    template: '<div v-if="modelValue" class="el-dialog"><h2>{{title}}</h2><slot /></div>'
  },
  ElButton: {
    name: 'ElButton',
    props: ['type', 'plain'],
    emits: ['click'],
    template: '<button class="el-button" @click="$emit(\'click\')"><slot /></button>'
  },
  ElText: {
    name: 'ElText',
    props: ['tag', 'size', 'type'],
    template: '<component :is="tag || \'span\'" :class="\'el-text\'"><slot /></component>'
  },
  ElTag: {
    name: 'ElTag',
    props: ['size', 'type'],
    template: '<span class="el-tag"><slot /></span>'
  },
  ElDescriptions: {
    name: 'ElDescriptions',
    props: ['column', 'border', 'size'],
    template: '<dl class="el-descriptions"><slot /></dl>'
  },
  ElDescriptionsItem: {
    name: 'ElDescriptionsItem',
    props: ['label'],
    template: '<div class="el-descriptions-item"><slot /></div>'
  },
  ElEmpty: {
    name: 'ElEmpty',
    props: ['description'],
    template: '<div class="el-empty">{{description}}</div>'
  }
}))

// ============ 辅助 ============

async function mountCitationLink(props: {
  visible?: boolean
  citation?: CitationPopupData | null
} = {}) {
  const { default: CitationLink } = await import(
    '@/components/report/CitationLink.vue'
  )
  return mount(CitationLink, {
    props: {
      visible: true,
      citation: null,
      ...props
    }
  })
}

const sampleCitation: CitationPopupData = {
  paperId: 'arxiv_2024_001',
  title: 'Large Language Models for Text Summarization',
  authors: ['Zhang, W.', 'Li, H.', 'Wang, J.'],
  year: 2024,
  text: 'Recent advances in large language models have shown promising results in text summarization tasks, achieving state-of-the-art performance across multiple benchmarks.',
  venue: 'ACL 2024'
}

describe('CitationLink', () => {
  it('visible=true 时弹窗应显示', async () => {
    const wrapper = await mountCitationLink({
      visible: true,
      citation: sampleCitation
    })
    expect(wrapper.find('.el-dialog').exists()).toBe(true)
  })

  it('visible=false 时弹窗应隐藏', async () => {
    const wrapper = await mountCitationLink({
      visible: false,
      citation: sampleCitation
    })
    expect(wrapper.find('.el-dialog').exists()).toBe(false)
  })

  it('应显示论文标题', async () => {
    const wrapper = await mountCitationLink({
      visible: true,
      citation: sampleCitation
    })
    expect(wrapper.find('h2').text()).toBe(sampleCitation.title)
  })

  it('无 title 时应显示 paperId', async () => {
    const wrapper = await mountCitationLink({
      visible: true,
      citation: { ...sampleCitation, title: undefined }
    })
    expect(wrapper.find('h2').text()).toBe('arxiv_2024_001')
  })

  it('应显示原文片段', async () => {
    const wrapper = await mountCitationLink({
      visible: true,
      citation: sampleCitation
    })
    const quote = wrapper.find('.el-text')
    expect(quote.exists()).toBe(true)
    expect(quote.text()).toContain('Recent advances')
  })

  it('点击查看详情应 emit go-detail + 关闭弹窗', async () => {
    const wrapper = await mountCitationLink({
      visible: true,
      citation: sampleCitation
    })
    const btn = wrapper.find('.el-button')
    expect(btn.exists()).toBe(true)
    await btn.trigger('click')
    await nextTick()

    expect(wrapper.emitted('go-detail')).toBeTruthy()
    expect(wrapper.emitted('go-detail')?.[0]).toEqual(['arxiv_2024_001'])
    expect(wrapper.emitted('update:visible')).toBeTruthy()
    expect(wrapper.emitted('update:visible')?.[0]).toEqual([false])
  })

  it('citation=null 时应显示空状态', async () => {
    const wrapper = await mountCitationLink({
      visible: true,
      citation: null
    })
    expect(wrapper.find('.el-empty').exists()).toBe(true)
    expect(wrapper.find('.el-empty').text()).toContain('引用信息不可用')
  })
})
