<script setup lang="ts">
/**
 * 点阵时钟组件（热力图风格）
 * - 26×9 网格点阵屏（CSS Grid），方形 LED 单元
 * - 5×7 点阵字体，每个数字之间隔 1 列空白
 * - HH:MM 显示，每分钟刷新
 * - 热力图渐变：点亮像素按位置分布深浅色阶，熄灭像素仅描边
 * - 冒号 1 秒闪烁一次
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'

// 5×7 点阵字模：0-9
const DIGIT_PATTERNS: Record<string, number[]> = {
  '0': [
    0b01110,
    0b10001,
    0b10011,
    0b10101,
    0b11001,
    0b10001,
    0b01110,
  ],
  '1': [
    0b00100,
    0b01100,
    0b00100,
    0b00100,
    0b00100,
    0b00100,
    0b01110,
  ],
  '2': [
    0b01110,
    0b10001,
    0b00001,
    0b00010,
    0b00100,
    0b01000,
    0b11111,
  ],
  '3': [
    0b01110,
    0b10001,
    0b00001,
    0b00110,
    0b00001,
    0b10001,
    0b01110,
  ],
  '4': [
    0b00010,
    0b00110,
    0b01010,
    0b10010,
    0b11111,
    0b00010,
    0b00010,
  ],
  '5': [
    0b11111,
    0b10000,
    0b11110,
    0b00001,
    0b00001,
    0b10001,
    0b01110,
  ],
  '6': [
    0b00110,
    0b01000,
    0b10000,
    0b11110,
    0b10001,
    0b10001,
    0b01110,
  ],
  '7': [
    0b11111,
    0b00001,
    0b00010,
    0b00100,
    0b01000,
    0b01000,
    0b01000,
  ],
  '8': [
    0b01110,
    0b10001,
    0b10001,
    0b01110,
    0b10001,
    0b10001,
    0b01110,
  ],
  '9': [
    0b01110,
    0b10001,
    0b10001,
    0b01111,
    0b00001,
    0b00010,
    0b01100,
  ],
}

// 冒号：1列宽，上下两个点亮像素
const COLON_PATTERN: number[] = [
  0b0,
  0b0,
  0b1,
  0b0,
  0b1,
  0b0,
  0b0,
]

// 布局：27列 × 9行
// 左边距(1) + H1(5)+gap(1)+H2(5)+gap(1)+colon(1)+gap(1)+M1(5)+gap(1)+M2(5)+gap(1) = 27
const COLS = 27
const ROWS = 9

// 字符布局：每个字符宽度 + 后面的间隔
const CHAR_LAYOUT = [
  { width: 5, gap: 1 }, // H1
  { width: 5, gap: 1 }, // H2
  { width: 1, gap: 1 }, // colon
  { width: 5, gap: 1 }, // M1
  { width: 5, gap: 1 }, // M2
]

const currentTime = ref('')
const colonVisible = ref(true)
let timer: ReturnType<typeof setInterval> | null = null
let colonTimer: ReturnType<typeof setInterval> | null = null

function updateTime() {
  const now = new Date()
  const h = String(now.getHours()).padStart(2, '0')
  const m = String(now.getMinutes()).padStart(2, '0')
  currentTime.value = `${h}:${m}`
}

// 构建 9×26 网格，值=热力强度(0=熄灭, 1-4=点亮色阶, -1=冒号点亮)
const gridPixels = computed(() => {
  const time = currentTime.value
  const grid: number[][] = Array.from({ length: ROWS }, () => Array(COLS).fill(0))

  if (!time) return grid

  const chars = [time[0], time[1], ':', time[3], time[4]]
  const patterns: { data: number[]; width: number }[] = []

  for (const ch of chars) {
    if (ch === ':') {
      patterns.push({ data: COLON_PATTERN, width: 1 })
    } else {
      patterns.push({ data: DIGIT_PATTERNS[ch] || DIGIT_PATTERNS['0'], width: 5 })
    }
  }

  const startRow = 1 // 字模7行在9行中居中：(9-7)/2=1

  let colOffset = 1 // 左侧留 1 列边距
  for (let d = 0; d < patterns.length; d++) {
    const { data: pattern, width: w } = patterns[d]
    for (let row = 0; row < 7; row++) {
      const bits = pattern[row]
      for (let col = 0; col < w; col++) {
        const bit = (bits >> (w - 1 - col)) & 1
        if (bit) {
          const r = row + startRow
          const c = colOffset + col
          if (chars[d] === ':') {
            grid[r][c] = -1
          } else {
            const centerRow = (ROWS - 1) / 2
            const centerCol = (COLS - 1) / 2
            const distRow = Math.abs(r - centerRow) / centerRow
            const distCol = Math.abs(c - centerCol) / centerCol
            const dist = (distRow + distCol) / 2
            let intensity = Math.round(4 - dist * 3)
            intensity += Math.floor(Math.random() * 2) - 1
            intensity = Math.max(1, Math.min(4, intensity))
            grid[r][c] = intensity
          }
        }
      }
    }
    colOffset += w + CHAR_LAYOUT[d].gap
  }

  return grid
})

function cellStyle(intensity: number) {
  // 熄灭像素：仅描边，无填充
  if (intensity === 0) {
    return { background: 'transparent', border: '1px solid #e4e7ed' }
  }
  // 冒号：闪烁
  if (intensity === -1) {
    if (!colonVisible.value) {
      return { background: 'transparent', border: '1px solid #e4e7ed' }
    }
    return {
      background: 'rgba(64, 158, 255, 0.9)',
      'box-shadow': '0 0 5px rgba(64, 158, 255, 0.45)',
    }
  }
  // 热力图色阶：1(最暗) → 4(最亮)
  const colors = [
    '',
    'rgba(64, 158, 255, 0.35)',
    'rgba(64, 158, 255, 0.55)',
    'rgba(64, 158, 255, 0.78)',
    'rgba(64, 158, 255, 1)',
  ]
  const shadows = [
    '',
    '0 0 2px rgba(64, 158, 255, 0.15)',
    '0 0 3px rgba(64, 158, 255, 0.25)',
    '0 0 4px rgba(64, 158, 255, 0.35)',
    '0 0 6px rgba(64, 158, 255, 0.5)',
  ]
  return {
    background: colors[intensity],
    'box-shadow': shadows[intensity],
  }
}

onMounted(() => {
  updateTime()
  const now = new Date()
  const msUntilNextMinute = (60 - now.getSeconds()) * 1000 - now.getMilliseconds()
  const firstTimeout = setTimeout(() => {
    updateTime()
    timer = setInterval(updateTime, 60000)
  }, msUntilNextMinute)

  colonTimer = setInterval(() => {
    colonVisible.value = !colonVisible.value
  }, 1000)

  onUnmounted(() => {
    clearTimeout(firstTimeout)
    if (timer) clearInterval(timer)
    if (colonTimer) clearInterval(colonTimer)
  })
})
</script>

<template>
  <div class="dot-matrix-clock">
    <div class="dot-matrix-clock__grid">
      <template v-for="row in ROWS" :key="'r' + row">
        <template v-for="col in COLS" :key="'c' + col">
          <div
            class="dot-matrix-clock__cell"
            :style="cellStyle(gridPixels[row - 1][col - 1])"
          />
        </template>
      </template>
    </div>
  </div>
</template>

<style scoped lang="scss">
.dot-matrix-clock {
  display: flex;
  justify-content: center;
  width: 100%;

  &__grid {
    display: grid;
    grid-template-columns: repeat(27, 1fr);
    grid-template-rows: repeat(9, 1fr);
    gap: 5px;
    width: 100%;
    aspect-ratio: 27 / 9;
  }

  &__cell {
    border-radius: 4px;
    box-sizing: border-box;
    transition: background 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
  }
}
</style>
