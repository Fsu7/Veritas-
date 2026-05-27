import { ref, computed, type Ref } from 'vue'

export function usePagination(
  total: Ref<number>,
  defaultPageSize: number = 10
) {
  const currentPage = ref(1)
  const pageSize = ref(defaultPageSize)

  const totalPages = computed(() =>
    Math.ceil(total.value / pageSize.value) || 1
  )

  function handleCurrentChange(
    page: number,
    callback: (page: number) => Promise<void>
  ) {
    currentPage.value = page
    callback(page)
  }

  function handleSizeChange(
    size: number,
    callback: (size: number) => Promise<void>
  ) {
    pageSize.value = size
    currentPage.value = 1
    callback(size)
  }

  function resetPage() {
    currentPage.value = 1
  }

  return {
    currentPage,
    pageSize,
    totalPages,
    handleCurrentChange,
    handleSizeChange,
    resetPage
  }
}
