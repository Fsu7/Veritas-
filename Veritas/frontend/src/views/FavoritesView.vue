<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePaperStore } from '@/stores/paperStore'
import PaperCard from '@/components/paper/PaperCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()
const paperStore = usePaperStore()

const currentPage = ref(1)
const pageSize = ref(10)

const favoritesList = computed(() => paperStore.favoritesList)
const total = computed(() => paperStore.favoritesTotal)
const loading = computed(() => paperStore.favoritesLoading)
const error = computed(() => paperStore.favoritesError)

async function loadFavorites() {
  try {
    await paperStore.fetchFavorites(currentPage.value, pageSize.value)
  } catch {
    // 错误已在 store 内捕获，此处仅提示
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadFavorites()
}

function handleSelectPaper(paperId: string) {
  router.push(`/paper/${paperId}`)
}

async function handleToggleFavorite(paperId: string) {
  try {
    await paperStore.toggleFavorite(paperId)
    ElMessage.success('已取消收藏')
    // 取消收藏后重新加载当前页
    await loadFavorites()
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  loadFavorites()
})
</script>

<template>
  <div v-loading="loading" class="favorites-view">
    <div class="favorites-view__content">
      <div class="favorites-view__header">
        <h1 class="favorites-view__title">我的收藏</h1>
        <el-tag type="info" effect="plain">
          共 {{ total }} 篇
        </el-tag>
      </div>

      <el-alert
        v-if="error"
        :title="error"
        type="error"
        show-icon
        :closable="false"
        class="favorites-view__error"
      />

      <el-row v-if="favoritesList.length > 0" :gutter="16">
        <el-col
          v-for="paper in favoritesList"
          :key="paper.paperId"
          :xs="24"
          :sm="12"
          :md="12"
          :lg="12"
        >
          <PaperCard
            :paper="paper"
            :is-favorited="true"
            @select="handleSelectPaper"
            @favorite="handleToggleFavorite"
          />
        </el-col>
      </el-row>

      <EmptyState
        v-else-if="!loading && !error"
        icon="folder"
        title="暂无收藏论文"
        description="去搜索并收藏感兴趣的论文吧"
        action-text="去搜索论文"
        @action="router.push('/search')"
      />

      <div v-if="total > pageSize" class="favorites-view__pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next, total"
          background
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/mixins' as *;

.favorites-view {
  padding: var(--spacing-lg);

  &__content {
    max-width: var(--content-max-width);
    margin: 0 auto;
  }

  &__header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
  }

  &__title {
    font-size: var(--font-size-xxl);
    font-weight: 600;
    margin: 0;
  }

  &__error {
    margin-bottom: var(--spacing-md);
  }

  &__pagination {
    display: flex;
    justify-content: center;
    margin-top: var(--spacing-lg);
  }
}

/* Task 50: 移动端响应式 */
@include respond-to(md) {
  .favorites-view {
    padding: var(--spacing-md);
  }

  .favorites-view__title {
    font-size: var(--font-size-xl);
  }

  .favorites-view__header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-sm);
  }
}
</style>
