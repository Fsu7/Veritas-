import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { effectScope } from 'vue'
import { useReplay, type PlaybackSpeed } from '@/composables/useReplay'
import type { ReplayFrame } from '@/types/agent'

/**
 * useReplay 单元测试
 * - 纯状态管理 + setInterval，无外部依赖
 * - 使用 vi.useFakeTimers 控制 setInterval
 * - 覆盖：play/pause 切换、seek 跳转、setSpeed 切换、播放结束自动暂停
 */

function makeFrames(count: number): ReplayFrame[] {
  return Array.from({ length: count }, (_, i) => ({
    timestamp: i * 1000,
    agentStates: {},
    event: {
      type: 'progress_update',
      data: { index: i },
      timestamp: i * 1000
    }
  }))
}

let scope: ReturnType<typeof effectScope>
let replay: ReturnType<typeof useReplay>

beforeEach(() => {
  vi.useFakeTimers()
  scope = effectScope()
  replay = scope.run(() => useReplay())!
})

afterEach(() => {
  // 清理所有定时器并停止 effect scope
  vi.clearAllTimers()
  scope.stop()
  vi.useRealTimers()
})

describe('useReplay', () => {
  describe('初始状态', () => {
    it('初始 isPlaying 为 false', () => {
      expect(replay.isPlaying.value).toBe(false)
    })

    it('初始 currentIndex 为 0', () => {
      expect(replay.currentIndex.value).toBe(0)
    })

    it('初始 playbackSpeed 为 1', () => {
      expect(replay.playbackSpeed.value).toBe(1)
    })

    it('初始 frames 为空数组', () => {
      expect(replay.frames.value).toEqual([])
      expect(replay.totalFrames.value).toBe(0)
    })

    it('空帧时 currentFrame 为 null', () => {
      expect(replay.currentFrame.value).toBeNull()
    })

    it('空帧时 progress 为 0', () => {
      expect(replay.progress.value).toBe(0)
    })
  })

  describe('loadFrames / clear', () => {
    it('loadFrames 加载帧并重置 currentIndex', () => {
      const frames = makeFrames(3)
      replay.loadFrames(frames)
      expect(replay.frames.value).toHaveLength(3)
      expect(replay.totalFrames.value).toBe(3)
      expect(replay.currentIndex.value).toBe(0)
      // currentFrame 是 computed 返回，用 toStrictEqual 做深比较
      expect(replay.currentFrame.value).toStrictEqual(frames[0])
    })

    it('loadFrames 会暂停当前播放', () => {
      const frames = makeFrames(3)
      replay.loadFrames(frames)
      replay.play()
      expect(replay.isPlaying.value).toBe(true)
      replay.loadFrames(makeFrames(2))
      expect(replay.isPlaying.value).toBe(false)
    })

    it('clear 清空帧并重置状态', () => {
      replay.loadFrames(makeFrames(3))
      replay.seek(2)
      replay.clear()
      expect(replay.frames.value).toEqual([])
      expect(replay.totalFrames.value).toBe(0)
      expect(replay.currentIndex.value).toBe(0)
      expect(replay.isPlaying.value).toBe(false)
    })
  })

  describe('play / pause 切换 isPlaying', () => {
    it('play 切换 isPlaying 为 true', () => {
      replay.loadFrames(makeFrames(3))
      replay.play()
      expect(replay.isPlaying.value).toBe(true)
    })

    it('pause 切换 isPlaying 为 false', () => {
      replay.loadFrames(makeFrames(3))
      replay.play()
      replay.pause()
      expect(replay.isPlaying.value).toBe(false)
    })

    it('空帧时 play 不生效', () => {
      replay.play()
      expect(replay.isPlaying.value).toBe(false)
    })

    it('play 在最后一帧时重置到第 0 帧', () => {
      const frames = makeFrames(3)
      replay.loadFrames(frames)
      replay.seek(2) // 最后一帧
      expect(replay.currentIndex.value).toBe(2)
      replay.play()
      expect(replay.currentIndex.value).toBe(0)
      expect(replay.isPlaying.value).toBe(true)
    })

    it('toggle 在暂停时启动播放', () => {
      replay.loadFrames(makeFrames(3))
      expect(replay.isPlaying.value).toBe(false)
      replay.toggle()
      expect(replay.isPlaying.value).toBe(true)
    })

    it('toggle 在播放时暂停', () => {
      replay.loadFrames(makeFrames(3))
      replay.play()
      replay.toggle()
      expect(replay.isPlaying.value).toBe(false)
    })

    it('play 后推进时间 currentIndex 递增', () => {
      replay.loadFrames(makeFrames(3))
      replay.play()
      expect(replay.currentIndex.value).toBe(0)
      vi.advanceTimersByTime(1000)
      expect(replay.currentIndex.value).toBe(1)
      vi.advanceTimersByTime(1000)
      expect(replay.currentIndex.value).toBe(2)
    })

    it('play 触发 onFrameChange 回调', () => {
      const onFrameChange = vi.fn()
      const localScope = effectScope()
      const localReplay = localScope.run(() => useReplay({ onFrameChange }))!
      localReplay.loadFrames(makeFrames(3))
      localReplay.play()
      // play 立即触发一次回调（frame 0）
      expect(onFrameChange).toHaveBeenCalledWith(expect.anything(), 0)
      vi.advanceTimersByTime(1000)
      expect(onFrameChange).toHaveBeenCalledWith(expect.anything(), 1)
      localScope.stop()
    })
  })

  describe('seek 跳转指定帧', () => {
    it('seek 跳转到指定索引', () => {
      replay.loadFrames(makeFrames(5))
      replay.seek(3)
      expect(replay.currentIndex.value).toBe(3)
    })

    it('seek 负数时 clamp 到 0', () => {
      replay.loadFrames(makeFrames(5))
      replay.seek(-1)
      expect(replay.currentIndex.value).toBe(0)
    })

    it('seek 超出上限时 clamp 到最后一帧', () => {
      replay.loadFrames(makeFrames(5))
      replay.seek(100)
      expect(replay.currentIndex.value).toBe(4)
    })

    it('seek 后 currentFrame 正确更新', () => {
      const frames = makeFrames(5)
      replay.loadFrames(frames)
      replay.seek(2)
      // currentFrame 是 computed 返回，用 toStrictEqual 做深比较
      expect(replay.currentFrame.value).toStrictEqual(frames[2])
    })

    it('seek 触发 onFrameChange 回调', () => {
      const onFrameChange = vi.fn()
      const localScope = effectScope()
      const localReplay = localScope.run(() => useReplay({ onFrameChange }))!
      localReplay.loadFrames(makeFrames(5))
      localReplay.seek(3)
      expect(onFrameChange).toHaveBeenCalledWith(expect.anything(), 3)
      localScope.stop()
    })

    it('seek 不影响 isPlaying 状态', () => {
      replay.loadFrames(makeFrames(5))
      replay.play()
      replay.seek(2)
      expect(replay.isPlaying.value).toBe(true)
    })
  })

  describe('setSpeed 切换 1x/2x/4x', () => {
    it('setSpeed(1) 设置 playbackSpeed 为 1', () => {
      replay.setSpeed(1 as PlaybackSpeed)
      expect(replay.playbackSpeed.value).toBe(1)
    })

    it('setSpeed(2) 设置 playbackSpeed 为 2', () => {
      replay.setSpeed(2 as PlaybackSpeed)
      expect(replay.playbackSpeed.value).toBe(2)
    })

    it('setSpeed(4) 设置 playbackSpeed 为 4', () => {
      replay.setSpeed(4 as PlaybackSpeed)
      expect(replay.playbackSpeed.value).toBe(4)
    })

    it('setSpeed(0.5) 设置 playbackSpeed 为 0.5', () => {
      replay.setSpeed(0.5 as PlaybackSpeed)
      expect(replay.playbackSpeed.value).toBe(0.5)
    })

    it('播放中 setSpeed 重新启动定时器以应用新速度', () => {
      replay.loadFrames(makeFrames(10))
      replay.play()
      // 1x: interval = 1000ms
      vi.advanceTimersByTime(1000)
      expect(replay.currentIndex.value).toBe(1)
      // 切换到 2x: interval = 500ms
      replay.setSpeed(2 as PlaybackSpeed)
      expect(replay.playbackSpeed.value).toBe(2)
      expect(replay.isPlaying.value).toBe(true)
      // 推进 500ms 应该前进一帧（2x 速度）
      vi.advanceTimersByTime(500)
      expect(replay.currentIndex.value).toBe(2)
    })

    it('暂停时 setSpeed 仅更新速度不启动播放', () => {
      replay.loadFrames(makeFrames(5))
      replay.setSpeed(4 as PlaybackSpeed)
      expect(replay.playbackSpeed.value).toBe(4)
      expect(replay.isPlaying.value).toBe(false)
    })

    it('4x 速度下帧间隔为 baseInterval/4', () => {
      replay.loadFrames(makeFrames(10))
      replay.setSpeed(4 as PlaybackSpeed)
      replay.play()
      // 4x: interval = 250ms
      vi.advanceTimersByTime(250)
      expect(replay.currentIndex.value).toBe(1)
      vi.advanceTimersByTime(250)
      expect(replay.currentIndex.value).toBe(2)
    })
  })

  describe('播放结束自动暂停', () => {
    it('播放到最后一帧自动暂停并触发 onComplete', () => {
      const onComplete = vi.fn()
      const localScope = effectScope()
      const localReplay = localScope.run(() => useReplay({ onComplete }))!
      localReplay.loadFrames(makeFrames(2))
      localReplay.play()
      expect(localReplay.isPlaying.value).toBe(true)
      // 推进 1000ms: currentIndex 0 -> 1
      vi.advanceTimersByTime(1000)
      expect(localReplay.currentIndex.value).toBe(1)
      expect(localReplay.isPlaying.value).toBe(true)
      // 再推进 1000ms: 已到最后一帧，触发 pause + onComplete
      vi.advanceTimersByTime(1000)
      expect(localReplay.currentIndex.value).toBe(1)
      expect(localReplay.isPlaying.value).toBe(false)
      expect(onComplete).toHaveBeenCalledTimes(1)
      localScope.stop()
    })

    it('播放结束后定时器已清理，不再推进', () => {
      replay.loadFrames(makeFrames(2))
      replay.play()
      vi.advanceTimersByTime(2000)
      expect(replay.isPlaying.value).toBe(false)
      const indexAtEnd = replay.currentIndex.value
      // 继续推进时间，currentIndex 不应变化
      vi.advanceTimersByTime(5000)
      expect(replay.currentIndex.value).toBe(indexAtEnd)
    })

    it('单帧播放立即结束', () => {
      const onComplete = vi.fn()
      const localScope = effectScope()
      const localReplay = localScope.run(() => useReplay({ onComplete }))!
      localReplay.loadFrames(makeFrames(1))
      localReplay.play()
      // 单帧：currentIndex(0) >= totalFrames-1(0)，定时器首次触发即结束
      vi.advanceTimersByTime(1000)
      expect(localReplay.isPlaying.value).toBe(false)
      expect(onComplete).toHaveBeenCalledTimes(1)
      localScope.stop()
    })
  })

  describe('reset / stepForward / stepBackward', () => {
    it('reset 暂停并重置 currentIndex 到 0', () => {
      replay.loadFrames(makeFrames(5))
      replay.seek(3)
      replay.play()
      replay.reset()
      expect(replay.isPlaying.value).toBe(false)
      expect(replay.currentIndex.value).toBe(0)
    })

    it('stepForward 前进一帧', () => {
      replay.loadFrames(makeFrames(5))
      replay.stepForward()
      expect(replay.currentIndex.value).toBe(1)
    })

    it('stepForward 在最后一帧时不越界', () => {
      replay.loadFrames(makeFrames(3))
      replay.seek(2)
      replay.stepForward()
      expect(replay.currentIndex.value).toBe(2)
    })

    it('stepBackward 后退一帧', () => {
      replay.loadFrames(makeFrames(5))
      replay.seek(3)
      replay.stepBackward()
      expect(replay.currentIndex.value).toBe(2)
    })

    it('stepBackward 在第 0 帧时不越界', () => {
      replay.loadFrames(makeFrames(3))
      replay.stepBackward()
      expect(replay.currentIndex.value).toBe(0)
    })
  })

  describe('progress 计算', () => {
    it('第 0 帧时 progress 为 0', () => {
      replay.loadFrames(makeFrames(5))
      expect(replay.progress.value).toBe(0)
    })

    it('最后一帧时 progress 为 100', () => {
      replay.loadFrames(makeFrames(5))
      replay.seek(4)
      expect(replay.progress.value).toBe(100)
    })

    it('中间帧 progress 按比例计算', () => {
      replay.loadFrames(makeFrames(5)) // totalFrames = 5
      replay.seek(2)
      // progress = 2 / (5-1) * 100 = 50
      expect(replay.progress.value).toBe(50)
    })

    it('空帧时 progress 为 0', () => {
      expect(replay.progress.value).toBe(0)
    })
  })

  describe('自定义 baseInterval', () => {
    it('自定义 baseInterval 影响播放间隔', () => {
      const localScope = effectScope()
      const localReplay = localScope.run(() => useReplay({ baseInterval: 500 }))!
      localReplay.loadFrames(makeFrames(5))
      localReplay.play()
      // 500ms 间隔
      vi.advanceTimersByTime(500)
      expect(localReplay.currentIndex.value).toBe(1)
      localScope.stop()
    })
  })

  describe('组件卸载清理', () => {
    it('scope 停止后定时器被清理', async () => {
      replay.loadFrames(makeFrames(10))
      replay.play()
      expect(replay.isPlaying.value).toBe(true)
      scope.stop()
      // 推进时间，currentIndex 不再变化（定时器已清理）
      const indexBefore = replay.currentIndex.value
      vi.advanceTimersByTime(5000)
      expect(replay.currentIndex.value).toBe(indexBefore)
    })
  })
})
