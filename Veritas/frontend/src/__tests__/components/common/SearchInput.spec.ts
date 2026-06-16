/**
 * SearchInput 组件测试
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import SearchInput from '@/components/common/SearchInput.vue'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, val: string) => { store[key] = val }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: () => { store = {} }
  }
})()

Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElInput: {
    name: 'ElInput',
    props: ['modelValue', 'placeholder', 'loading', 'disabled', 'size', 'clearable'],
    emits: ['update:modelValue', 'keyup', 'clear'],
    template: '<input class="el-input" :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', $event.target.value)" @keyup="$emit(\'keyup\', $event)" />'
  },
  ElIcon: { template: '<i class="el-icon"><slot /></i>' },
  ElTag: {
    name: 'ElTag',
    props: ['size'],
    emits: ['click'],
    template: '<span class="el-tag" @click="$emit(\'click\')"><slot /></span>'
  },
  Search: { template: '<i>search</i>' }
}))

vi.mock('@element-plus/icons-vue', () => ({
  Search: { template: '<i>search</i>' }
}))

async function mountSearchInput(props: {
  modelValue?: string
  placeholder?: string
  loading?: boolean
} = {}) {
  return mount(SearchInput, {
    props: {
      modelValue: '',
      ...props
    }
  })
}

describe('SearchInput', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorageMock.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('输入变化后 300ms 应 emit search', async () => {
    const wrapper = await mountSearchInput()
    const input = wrapper.find('.el-input')
    await input.setValue('test query')
    await nextTick()

    // 300ms 内不应触发
    vi.advanceTimersByTime(200)
    await nextTick()
    expect(wrapper.emitted('search')).toBeFalsy()

    // 300ms 后应触发
    vi.advanceTimersByTime(150)
    await nextTick()
    expect(wrapper.emitted('search')).toBeTruthy()
  })

  it('回车应立即触发搜索', async () => {
    const wrapper = await mountSearchInput()
    const input = wrapper.find('.el-input')
    await input.setValue('instant query')
    await nextTick()

    await input.trigger('keyup.enter')
    await nextTick()

    expect(wrapper.emitted('search')).toBeTruthy()
  })
})
