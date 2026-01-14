'use client';

import { useRef, useState, useEffect, useCallback } from 'react';

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
}

export interface GazeConfig {
  /** 获取当前可见文本的函数 */
  getVisibleText: () => string;
}

// ============================================
// Constants
// ============================================

const GAZE_TO_OBSERVING_MS = 5000;  // 5秒 -> 开始观察（预触发）
const GAZE_TO_READY_MS = 8000;      // 8秒 -> 准备好（触发洞察）
const MOUSE_MOVE_THRESHOLD = 50;    // 鼠标移动超过 50px 算作活动
const SCROLL_THRESHOLD = 200;       // 滚动超过 200px 算作换位置

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
  });

  // 追踪用户活动
  const lastActivityTime = useRef(Date.now());
  const lastMousePos = useRef({ x: 0, y: 0 });
  const lastReadyScrollPos = useRef(0);  // ready 时的滚动位置
  const hasScrolledAfterReady = useRef(true); // 是否在 ready 后滚动过（初始 true 允许首次触发）
  const isActive = useRef(true); // 页面是否在前台
  const scrollListenerBound = useRef(false); // 滚动监听器是否已绑定

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
      if (dx > MOUSE_MOVE_THRESHOLD || dy > MOUSE_MOVE_THRESHOLD) {
        lastMousePos.current = { x: e.clientX, y: e.clientY };
        resetGaze();
      }
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [resetGaze]);

  // 监听滚动 - 使用轮询方式确保绑定
  useEffect(() => {
    const handleScroll = () => {
      const container = scrollContainerRef.current;
      if (!container) return;

      const currentScrollTop = container.scrollTop;
      const scrollDelta = Math.abs(currentScrollTop - lastReadyScrollPos.current);

      // 如果滚动距离超过阈值，标记为已滚动（可以再次触发洞察）
      if (scrollDelta > SCROLL_THRESHOLD) {
        hasScrolledAfterReady.current = true;
      }

      resetGaze();
    };

    // 轮询检查容器是否就绪
    const checkAndBind = () => {
      const container = scrollContainerRef.current;
      if (container && !scrollListenerBound.current) {
        container.addEventListener('scroll', handleScroll, { passive: true });
        scrollListenerBound.current = true;
      }
    };

    checkAndBind();

    const interval = setInterval(() => {
      if (!scrollListenerBound.current) {
        checkAndBind();
      }
    }, 500);

    return () => {
      clearInterval(interval);
      const container = scrollContainerRef.current;
      if (container) {
        container.removeEventListener('scroll', handleScroll);
      }
      scrollListenerBound.current = false;
    };
  }, [scrollContainerRef, resetGaze]);

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
      const canTrigger = hasScrolledAfterReady.current;
      const container = scrollContainerRef.current;

      setDetection(prev => {
        let newState = prev.state;
        let shouldMarkReady = false;

        // 状态转换逻辑
        if (prev.state === 'idle') {
          // idle -> observing: 凝视超过 5 秒，且用户已滚动到新位置
          if (gazeTime >= GAZE_TO_OBSERVING_MS && canTrigger) {
            newState = 'observing';
          }
        } else if (prev.state === 'observing') {
          // observing -> ready: 凝视超过 8 秒
          if (gazeTime >= GAZE_TO_READY_MS) {
            newState = 'ready';
            shouldMarkReady = true;
          }
          // observing -> idle: 有活动（gazeTime 被重置）
          else if (gazeTime < GAZE_TO_OBSERVING_MS) {
            newState = 'idle';
          }
        } else if (prev.state === 'ready') {
          // ready -> idle: 有新活动时回到 idle
          if (gazeTime < GAZE_TO_OBSERVING_MS) {
            newState = 'idle';
          }
        }

        const stateChanged = newState !== prev.state;

        // 在状态变为 ready 时，记录滚动位置并标记
        if (shouldMarkReady && container) {
          lastReadyScrollPos.current = container.scrollTop;
          hasScrolledAfterReady.current = false;
        }

        // 获取文本（仅在状态变为 ready 时）
        let focusedText = prev.focusedText;
        if (stateChanged && newState === 'ready') {
          focusedText = config.getVisibleText();
        }

        return {
          state: newState,
          gazeTime,
          stateJustChanged: stateChanged,
          focusedText,
        };
      });
    }, 200); // 每 200ms 检测一次

    return () => clearInterval(interval);
  }, [config, scrollContainerRef]);

  return detection;
}
