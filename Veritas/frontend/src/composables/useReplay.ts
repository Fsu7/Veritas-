/**
 * Agent 流程回放 composable
 * - 接收回放帧数组，提供播放/暂停/进度控制
 * - 支持 0.5x / 1x / 2x / 4x 倍速
 * - 通过 setInterval 推进帧
 * - onScopeDispose 自动清理定时器
 */
import { ref, computed, onScopeDispose, type Ref, type ComputedRef } from 'vue'
import type { ReplayFrame } from '@/types/agent'

export type PlaybackSpeed = 0.5 | 1 | 2 | 4

export interface UseReplayOptions {
  /** 帧间基础间隔（ms），实际间隔 = baseInterval / speed */
  baseInterval?: number
  /** 帧变化回调 */
  onFrameChange?: (frame: ReplayFrame, index: number) => void
  /** 回放结束回调 */
  onComplete?: () => void
}

export interface UseReplayReturn {
  frames: Ref<ReplayFrame[]>
  isPlaying: Ref<boolean>
  currentIndex: Ref<number>
  playbackSpeed: Ref<PlaybackSpeed>
  currentFrame: ComputedRef<ReplayFrame | null>
  progress: ComputedRef<number>
  totalFrames: ComputedRef<number>
  play: () => void
  pause: () => void
  toggle: () => void
  reset: () => void
  seek: (index: number) => void
  stepForward: () => void
  stepBackward: () => void
  setSpeed: (speed: PlaybackSpeed) => void
  loadFrames: (frames: ReplayFrame[]) => void
  clear: () => void
}

const DEFAULT_BASE_INTERVAL = 1000

export function useReplay(options: UseReplayOptions = {}): UseReplayReturn {
  const {
    baseInterval = DEFAULT_BASE_INTERVAL,
    onFrameChange,
    onComplete
  } = options

  const frames = ref<ReplayFrame[]>([])
  const isPlaying = ref(false)
  const currentIndex = ref(0)
  const playbackSpeed = ref<PlaybackSpeed>(1)

  let playTimer: ReturnType<typeof setInterval> | null = null

  const totalFrames = computed(() => frames.value.length)
  const currentFrame = computed<ReplayFrame | null>(() =>
    frames.value[currentIndex.value] ?? null
  )
  const progress = computed(() => {
    if (totalFrames.value === 0) return 0
    return Math.round((currentIndex.value / (totalFrames.value - 1)) * 100)
  })

  function clearTimer() {
    if (playTimer) {
      clearInterval(playTimer)
      playTimer = null
    }
  }

  function notifyFrameChange() {
    const frame = currentFrame.value
    if (frame && onFrameChange) {
      onFrameChange(frame, currentIndex.value)
    }
  }

  function play() {
    if (frames.value.length === 0) return
    if (currentIndex.value >= totalFrames.value - 1) {
      currentIndex.value = 0
    }
    isPlaying.value = true
    clearTimer()
    const interval = baseInterval / playbackSpeed.value
    playTimer = setInterval(() => {
      if (currentIndex.value >= totalFrames.value - 1) {
        pause()
        if (onComplete) onComplete()
        return
      }
      currentIndex.value++
      notifyFrameChange()
    }, interval)
    notifyFrameChange()
  }

  function pause() {
    isPlaying.value = false
    clearTimer()
  }

  function toggle() {
    if (isPlaying.value) {
      pause()
    } else {
      play()
    }
  }

  function reset() {
    pause()
    currentIndex.value = 0
    notifyFrameChange()
  }

  function seek(index: number) {
    const clamped = Math.max(0, Math.min(index, totalFrames.value - 1))
    currentIndex.value = clamped
    notifyFrameChange()
  }

  function stepForward() {
    if (currentIndex.value < totalFrames.value - 1) {
      currentIndex.value++
      notifyFrameChange()
    }
  }

  function stepBackward() {
    if (currentIndex.value > 0) {
      currentIndex.value--
      notifyFrameChange()
    }
  }

  function setSpeed(speed: PlaybackSpeed) {
    playbackSpeed.value = speed
    if (isPlaying.value) {
      // 重新启动定时器以应用新速度
      play()
    }
  }

  function loadFrames(newFrames: ReplayFrame[]) {
    pause()
    frames.value = newFrames
    currentIndex.value = 0
  }

  function clear() {
    pause()
    frames.value = []
    currentIndex.value = 0
  }

  onScopeDispose(() => {
    clearTimer()
  })

  return {
    frames,
    isPlaying,
    currentIndex,
    playbackSpeed,
    currentFrame,
    progress,
    totalFrames,
    play,
    pause,
    toggle,
    reset,
    seek,
    stepForward,
    stepBackward,
    setSpeed,
    loadFrames,
    clear
  }
}
