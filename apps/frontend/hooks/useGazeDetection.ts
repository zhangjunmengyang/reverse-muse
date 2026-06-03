'use client';

import { useRef, useState, useEffect, useCallback } from 'react';

import {
  decideReadingTrigger,
  type PassiveTriggerType,
  type TriggerDecisionReason,
} from '@/lib/readingTriggerPolicy';
import type { ReadingTriggerConfig } from '@/lib/readingTriggerConfig';

// ============================================
// Types
// ============================================

export type GazeState = 'idle' | 'observing' | 'ready';

export interface GazeDetection {
  /** 当前状态 */
  state: GazeState;
  /** 凝视时间 (ms) */
  gazeTime: number;
  /** 状态刚刚改变 */
  stateJustChanged: boolean;
  /** 当前页面的文本内容 */
  focusedText: string;
  /** 一次性触发事件 ID */
  triggerId: number;
  /** 建议触发类型 */
  triggerType: PassiveTriggerType | null;
  /** 触发原因，用于调试 */
  triggerReason: TriggerDecisionReason | null;
}

export interface GazeConfig {
  /** 获取当前可见文本的函数 */
  getVisibleText: () => string;
  /** 主动触发阈值配置 */
  triggerConfig: ReadingTriggerConfig;
}

// ============================================
// Hook
// ============================================

export function useGazeDetection(
  scrollContainerRef: React.RefObject<HTMLElement | null>,
  config: GazeConfig
): GazeDetection {
  const [detection, setDetection] = useState<GazeDetection>({
    state: 'idle',
    gazeTime: 0,
    stateJustChanged: false,
    focusedText: '',
    triggerId: 0,
    triggerType: null,
    triggerReason: null,
  });

  // 追踪用户活动
  const lastActivityTime = useRef(Date.now());
  const lastMousePos = useRef({ x: 0, y: 0 });
  const paperLoadedAt = useRef(Date.now());
  const lastScrollTop = useRef(0);
  const backtrackDistancePx = useRef(0);
  const lastTriggerAt = useRef(0);
  const lastTriggerByText = useRef<Record<string, number>>({});
  const isActive = useRef(true); // 页面是否在前台
  const boundScrollContainer = useRef<HTMLElement | null>(null);

  // 重置凝视计时
  const resetGaze = useCallback(() => {
    lastActivityTime.current = Date.now();
  }, []);

  // 监听鼠标移动
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const dx = Math.abs(e.clientX - lastMousePos.current.x);
      const dy = Math.abs(e.clientY - lastMousePos.current.y);

      // 只有移动超过阈值才算活动
      if (
        dx > config.triggerConfig.mouseMoveThresholdPx
        || dy > config.triggerConfig.mouseMoveThresholdPx
      ) {
        lastMousePos.current = { x: e.clientX, y: e.clientY };
        resetGaze();
      }
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [config.triggerConfig.mouseMoveThresholdPx, resetGaze]);

  // 监听滚动 - 使用轮询方式确保绑定
  useEffect(() => {
    const handleScroll = () => {
      const container = scrollContainerRef.current;
      if (!container) return;

      const previousScrollTop = lastScrollTop.current;
      const currentScrollTop = container.scrollTop;
      const scrollDelta = currentScrollTop - previousScrollTop;

      if (scrollDelta < 0) {
        backtrackDistancePx.current += Math.abs(scrollDelta);
      } else if (scrollDelta > 80) {
        backtrackDistancePx.current = 0;
      }

      lastScrollTop.current = currentScrollTop;

      if (Math.abs(scrollDelta) > config.triggerConfig.scrollActivityThresholdPx) {
        resetGaze();
      }
    };

    // 轮询检查容器是否就绪；PDF 切换时同步重新绑定新容器。
    const checkAndBind = () => {
      const container = scrollContainerRef.current;
      if (container === boundScrollContainer.current) {
        return;
      }

      if (boundScrollContainer.current) {
        boundScrollContainer.current.removeEventListener('scroll', handleScroll);
      }

      if (container) {
        paperLoadedAt.current = Date.now();
        lastScrollTop.current = container.scrollTop;
        backtrackDistancePx.current = 0;
        container.addEventListener('scroll', handleScroll, { passive: true });
      }

      boundScrollContainer.current = container;
    };

    checkAndBind();

    const interval = setInterval(() => {
      checkAndBind();
    }, 500);

    return () => {
      clearInterval(interval);
      const container = boundScrollContainer.current;
      if (container) {
        container.removeEventListener('scroll', handleScroll);
      }
      boundScrollContainer.current = null;
    };
  }, [config.triggerConfig.scrollActivityThresholdPx, scrollContainerRef, resetGaze]);

  // 监听键盘
  useEffect(() => {
    const handleKeyDown = () => {
      resetGaze();
    };

    window.addEventListener('keydown', handleKeyDown, { passive: true });
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [resetGaze]);

  // 监听点击
  useEffect(() => {
    const handleClick = () => {
      resetGaze();
    };

    window.addEventListener('click', handleClick, { passive: true });
    return () => window.removeEventListener('click', handleClick);
  }, [resetGaze]);

  // 监听页面可见性
  useEffect(() => {
    const handleVisibility = () => {
      if (document.hidden) {
        isActive.current = false;
      } else {
        isActive.current = true;
        resetGaze(); // 切回来时重置
      }
    };

    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [resetGaze]);

  // 定时检测凝视状态
  useEffect(() => {
    const interval = setInterval(() => {
      if (!isActive.current) return;

      const now = Date.now();
      const gazeTime = now - lastActivityTime.current;
      const container = scrollContainerRef.current;
      const visibleText = config.getVisibleText();
      const decision = decideReadingTrigger({
        now,
        paperLoadedAt: paperLoadedAt.current,
        idleMs: gazeTime,
        visibleText,
        scrollTop: container?.scrollTop ?? 0,
        backtrackDistancePx: backtrackDistancePx.current,
        lastTriggerAt: lastTriggerAt.current,
        lastTriggerByText: lastTriggerByText.current,
        config: config.triggerConfig,
      });

      setDetection(prev => {
        let newState = prev.state;

        // 状态转换逻辑。ready 代表本轮已经建议触发。
        if (prev.state === 'idle') {
          if (gazeTime >= config.triggerConfig.observingMs) {
            newState = 'observing';
          }
        } else if (prev.state === 'observing') {
          if (decision.shouldTrigger) {
            newState = 'ready';
          }
          else if (gazeTime < config.triggerConfig.observingMs) {
            newState = 'idle';
          }
        } else if (prev.state === 'ready') {
          if (gazeTime < config.triggerConfig.observingMs) {
            newState = 'idle';
          }
        }

        const stateChanged = newState !== prev.state;
        const shouldEmitTrigger = decision.shouldTrigger && newState === 'ready' && prev.state !== 'ready';

        if (shouldEmitTrigger) {
          lastTriggerAt.current = now;
          lastTriggerByText.current[decision.textSignature] = now;
          backtrackDistancePx.current = 0;
          lastActivityTime.current = now;
        }

        return {
          state: newState,
          gazeTime,
          stateJustChanged: stateChanged,
          focusedText: shouldEmitTrigger ? decision.text : prev.focusedText,
          triggerId: shouldEmitTrigger ? prev.triggerId + 1 : prev.triggerId,
          triggerType: shouldEmitTrigger ? decision.triggerType ?? null : prev.triggerType,
          triggerReason: shouldEmitTrigger ? decision.reason : prev.triggerReason,
        };
      });
    }, 200); // 每 200ms 检测一次

    return () => clearInterval(interval);
  }, [config, scrollContainerRef]);

  return detection;
}
