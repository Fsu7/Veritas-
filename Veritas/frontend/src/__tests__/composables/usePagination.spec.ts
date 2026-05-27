import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { usePagination } from '@/composables/usePagination'

describe('usePagination', () => {
  it('initializes with default page size', () => {
    const total = ref(0)
    const { currentPage, pageSize, totalPages } = usePagination(total)
    expect(currentPage.value).toBe(1)
    expect(pageSize.value).toBe(10)
    expect(totalPages.value).toBe(1)
  })

  it('initializes with custom page size', () => {
    const total = ref(0)
    const { pageSize } = usePagination(total, 20)
    expect(pageSize.value).toBe(20)
  })

  it('calculates totalPages correctly', () => {
    const total = ref(25)
    const { totalPages } = usePagination(total, 10)
    expect(totalPages.value).toBe(3)
  })

  it('returns 1 when total is 0', () => {
    const total = ref(0)
    const { totalPages } = usePagination(total)
    expect(totalPages.value).toBe(1)
  })

  it('returns 1 when total equals pageSize', () => {
    const total = ref(10)
    const { totalPages } = usePagination(total, 10)
    expect(totalPages.value).toBe(1)
  })

  it('handleCurrentChange updates currentPage and calls callback', () => {
    const total = ref(30)
    const callback = vi.fn().mockResolvedValue(undefined)
    const { currentPage, handleCurrentChange } = usePagination(total)

    handleCurrentChange(2, callback)
    expect(currentPage.value).toBe(2)
    expect(callback).toHaveBeenCalledWith(2)
  })

  it('handleSizeChange updates pageSize, resets currentPage to 1, and calls callback', () => {
    const total = ref(30)
    const callback = vi.fn().mockResolvedValue(undefined)
    const { currentPage, pageSize, handleSizeChange } = usePagination(total)

    handleSizeChange(20, callback)
    expect(pageSize.value).toBe(20)
    expect(currentPage.value).toBe(1)
    expect(callback).toHaveBeenCalledWith(20)
  })

  it('resetPage sets currentPage to 1', () => {
    const total = ref(30)
    const callback = vi.fn().mockResolvedValue(undefined)
    const { currentPage, handleCurrentChange, resetPage } = usePagination(total)

    handleCurrentChange(3, callback)
    expect(currentPage.value).toBe(3)

    resetPage()
    expect(currentPage.value).toBe(1)
  })

  it('reacts to total changes', () => {
    const total = ref(25)
    const { totalPages } = usePagination(total, 10)
    expect(totalPages.value).toBe(3)

    total.value = 100
    expect(totalPages.value).toBe(10)
  })
})
