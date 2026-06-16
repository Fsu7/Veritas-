/**
 * FilterPanel 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import FilterPanel from '@/components/common/FilterPanel.vue'

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElInput: {
    name: 'ElInput',
    props: ['modelValue', 'placeholder', 'type', 'min', 'max', 'size', 'clearable'],
    emits: ['update:modelValue'],
    template: '<input class="el-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />'
  },
  ElSelect: {
    name: 'ElSelect',
    props: ['modelValue', 'multiple', 'placeholder', 'size', 'style', 'collapseTags', 'collapseTagsTooltip'],
    emits: ['update:modelValue'],
    template: '<select class="el-select" multiple :value="modelValue" @change="$emit(\'update:modelValue\', Array.from($event.target.selectedOptions).map(o=>o.value))"><slot /></select>'
  },
  ElOption: {
    name: 'ElOption',
    props: ['label', 'value'],
    template: '<option :value="value">{{label}}</option>'
  },
  ElInputNumber: {
    name: 'ElInputNumber',
    props: ['modelValue', 'min', 'size', 'style'],
    emits: ['update:modelValue'],
    template: '<input class="el-input-number" type="number" :value="modelValue" @input="$emit(\'update:modelValue\', Number($event.target.value))" />'
  },
  ElButton: {
    name: 'ElButton',
    props: ['size'],
    emits: ['click'],
    template: '<button class="el-button" @click="$emit(\'click\')"><slot /></button>'
  }
}))

async function mountFilterPanel(props: {
  filters?: Record<string, unknown>
  conferences?: string[]
} = {}) {
  return mount(FilterPanel, {
    props: {
      filters: {},
      ...props.filters ? { filters: props.filters } : {},
      conferences: props.conferences
    }
  })
}

describe('FilterPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应渲染年份输入框', async () => {
    const wrapper = await mountFilterPanel()
    const inputs = wrapper.findAll('.el-input')
    expect(inputs.length).toBeGreaterThanOrEqual(2)
  })

  it('应渲染会议选择器', async () => {
    const wrapper = await mountFilterPanel()
    expect(wrapper.find('.el-select').exists()).toBe(true)
  })

  it('应渲染引用数输入', async () => {
    const wrapper = await mountFilterPanel()
    expect(wrapper.find('.el-input-number').exists()).toBe(true)
  })

  it('应渲染重置按钮', async () => {
    const wrapper = await mountFilterPanel()
    const resetBtn = wrapper.find('.el-button')
    expect(resetBtn.exists()).toBe(true)
    expect(resetBtn.text()).toContain('重置')
  })

  it('点击重置应 emit reset', async () => {
    const wrapper = await mountFilterPanel()
    const resetBtn = wrapper.find('.el-button')
    await resetBtn.trigger('click')
    expect(wrapper.emitted('reset')).toBeTruthy()
  })

  it('更改年份应 emit update:filters', async () => {
    const wrapper = await mountFilterPanel()
    const yearInput = wrapper.findAll('.el-input')[0]
    await yearInput.setValue('2020')
    await nextTick()

    expect(wrapper.emitted('update:filters')).toBeTruthy()
  })
})
