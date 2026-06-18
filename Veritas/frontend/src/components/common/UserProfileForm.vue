<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/userStore'
import type { UserProfile } from '@/types/user'

const props = defineProps<{
  initialData?: UserProfile
}>()

const emit = defineEmits<{
  (e: 'saved', profile: UserProfile): void
}>()

const userStore = useUserStore()
const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive<UserProfile>({
  educationLevel: 'master',
  researchField: '',
  knowledgeLevel: 'intermediate',
  preferredStyle: 'balanced'
})

// 记录初始数据快照，用于重置表单
const initialSnapshot = reactive<UserProfile>({ ...form })

function syncFromInitial(data: UserProfile) {
  form.educationLevel = data.educationLevel
  form.researchField = data.researchField
  form.knowledgeLevel = data.knowledgeLevel
  form.preferredStyle = data.preferredStyle
  initialSnapshot.educationLevel = data.educationLevel
  initialSnapshot.researchField = data.researchField
  initialSnapshot.knowledgeLevel = data.knowledgeLevel
  initialSnapshot.preferredStyle = data.preferredStyle
}

const educationOptions = [
  { label: '本科生', value: 'undergraduate' as const },
  { label: '硕士研究生', value: 'master' as const },
  { label: '博士研究生', value: 'phd' as const },
  { label: '教师/研究者', value: 'faculty' as const }
]

const knowledgeOptions = [
  { label: '初级（对该领域了解较少）', value: 'beginner' as const },
  { label: '中级（有基础了解）', value: 'intermediate' as const },
  { label: '高级（深入研究）', value: 'advanced' as const },
  { label: '专家（领域权威）', value: 'expert' as const }
]

const styleOptions = [
  { label: '通俗（日常用语+比喻）', value: 'simple' as const },
  { label: '均衡（标准学术表达）', value: 'balanced' as const },
  { label: '专业（正式学术+引用）', value: 'technical' as const }
]

const rules: FormRules = {
  educationLevel: [
    { required: true, message: '请选择学历层次', trigger: 'change' }
  ],
  researchField: [
    { required: true, message: '请输入研究方向', trigger: 'blur' }
  ],
  knowledgeLevel: [
    { required: true, message: '请选择知识水平', trigger: 'change' }
  ],
  preferredStyle: [
    { required: true, message: '请选择偏好风格', trigger: 'change' }
  ]
}

watch(
  () => props.initialData,
  (data) => {
    if (data) {
      syncFromInitial(data)
    }
  },
  { immediate: true }
)

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload: UserProfile = { ...form }
    await userStore.saveProfile(payload)
    // 保存成功后同步快照，便于后续重置
    initialSnapshot.educationLevel = form.educationLevel
    initialSnapshot.researchField = form.researchField
    initialSnapshot.knowledgeLevel = form.knowledgeLevel
    initialSnapshot.preferredStyle = form.preferredStyle
    ElMessage.success('画像保存成功')
    emit('saved', payload)
  } catch {
    ElMessage.error('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

function handleReset() {
  // 重置为最近一次保存的快照（或初始数据）
  form.educationLevel = initialSnapshot.educationLevel
  form.researchField = initialSnapshot.researchField
  form.knowledgeLevel = initialSnapshot.knowledgeLevel
  form.preferredStyle = initialSnapshot.preferredStyle
  formRef.value?.clearValidate()
}
</script>

<template>
  <el-form
    ref="formRef"
    :model="form"
    :rules="rules"
    label-position="top"
    class="profile-form"
  >
    <el-form-item label="学历层次" prop="educationLevel">
      <el-select
        v-model="form.educationLevel"
        placeholder="请选择学历层次"
        :disabled="saving"
        class="profile-form__select"
      >
        <el-option
          v-for="opt in educationOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </el-form-item>

    <el-form-item label="研究方向" prop="researchField">
      <el-input
        v-model="form.researchField"
        placeholder="如：NLP、计算机视觉、强化学习"
        :disabled="saving"
      />
    </el-form-item>

    <el-form-item label="知识水平" prop="knowledgeLevel">
      <el-select
        v-model="form.knowledgeLevel"
        placeholder="请选择知识水平"
        :disabled="saving"
        class="profile-form__select"
      >
        <el-option
          v-for="opt in knowledgeOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </el-form-item>

    <el-form-item label="偏好风格" prop="preferredStyle">
      <el-select
        v-model="form.preferredStyle"
        placeholder="请选择偏好风格"
        :disabled="saving"
        class="profile-form__select"
      >
        <el-option
          v-for="opt in styleOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </el-form-item>

    <el-form-item>
      <el-button
        type="primary"
        :loading="saving"
        @click="handleSave"
      >
        保存画像
      </el-button>
      <el-button
        :disabled="saving"
        @click="handleReset"
      >
        重置
      </el-button>
    </el-form-item>
  </el-form>
</template>

<style scoped lang="scss">
.profile-form {
  &__select {
    width: 100%;
  }
}
</style>
