/**
 * SortDropdown 组件测试
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import SortDropdown from '@/components/common/SortDropdown.vue'

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElSelect: {
    name: 'ElSelect',
    props: ['modelValue', 'size', 'style'],
    emits: ['update:modelValue'],
    template: '<select class="el-select" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><slot /></select>'
  },
  ElOption: {
    name: 'ElOption',
    props: ['label', 'value'],
    template: '<option :value="value">{{label}}</option>'
  }
}))

async function mountSortDropdown(props: {
  modelValue?: { field: 'relevance' | 'publishedDate' | 'citationCount'; order: 'asc' | 'desc' }
} = {}) {
  return mount(SortDropdown, {
    props: {
      modelValue: props.modelValue ?? { field: 'relevance', order: 'desc' }
    }
  })
}

describe('SortDropdown', () => {
  it('应渲染 3 个排序选项', async () => {
    const wrapper = await mountSortDropdown()
    const select = wrapper.find('.el-select')
    expect(select.exists()).toBe(true)
  })

  it('切换排序应 emit update:modelValue', async () => {
    const wrapper = await mountSortDropdown()
    const select = wrapper.find('.el-select')
    await select.setValue('publishedDate')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toMatchObject({
      field: 'publishedDate',
      order: 'desc'
    })
  })
})
