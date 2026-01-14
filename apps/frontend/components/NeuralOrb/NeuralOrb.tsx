'use client';

import React, { useEffect, useState, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import styles from './NeuralOrb.module.css';

// ============================================
// Types
// ============================================

export type OrbState = 'idle' | 'observing' | 'ready' | 'speaking';

export interface NeuralOrbProps {
  state: OrbState;
  visible?: boolean;
  message?: string;
  isStreaming?: boolean;
  onDismiss?: () => void;
  autoDismissDelay?: number;
}

// ============================================
// State Configurations
// ============================================

interface StateConfig {
  colors: string[];
  speed: number;
  glow: string;
  blur: number;
}

// iOS 18 Siri-inspired: 主色调 + 彩虹点缀，创造流动感
const CONFIGS: Record<OrbState, StateConfig> = {
  idle: {
    // 紫色主调 + 蓝粉点缀
    colors: [
      '#a855f7', // 紫色 (主)
      '#ec4899', // 粉色
      '#6366f1', // 靛蓝
      '#c084fc', // 浅紫
      '#3b82f6', // 蓝色
      '#f472b6', // 浅粉
      '#8b5cf6', // 紫罗兰
      '#06b6d4', // 青色点缀
    ],
    speed: 5,
    glow: '#a78bfa',
    blur: 20,
  },
  observing: {
    // 蓝色主调 + 紫青点缀
    colors: [
      '#3b82f6', // 蓝色 (主)
      '#8b5cf6', // 紫色
      '#06b6d4', // 青色
      '#60a5fa', // 浅蓝
      '#a855f7', // 紫色
      '#22d3ee', // 亮青
      '#6366f1', // 靛蓝
      '#14b8a6', // 青绿点缀
    ],
    speed: 4,
    glow: '#38bdf8',
    blur: 22,
  },
  ready: {
    // 绿色主调 + 青蓝黄点缀
    colors: [
      '#10b981', // 翠绿 (主)
      '#06b6d4', // 青色
      '#22c55e', // 绿色
      '#3b82f6', // 蓝色点缀
      '#14b8a6', // 青绿
      '#fbbf24', // 金黄点缀
      '#34d399', // 浅绿
      '#8b5cf6', // 紫色点缀
    ],
    speed: 3,
    glow: '#10b981',
    blur: 24,
  },
  speaking: {
    // 橙色主调 + 红粉黄点缀
    colors: [
      '#f97316', // 橙色 (主)
      '#ef4444', // 红色
      '#fbbf24', // 金黄
      '#ec4899', // 粉色点缀
      '#f59e0b', // 琥珀
      '#fb7185', // 玫瑰红
      '#facc15', // 黄色
      '#a855f7', // 紫色点缀
    ],
    speed: 3.5,
    glow: '#fbbf24',
    blur: 22,
  },
};

// ============================================
// Color utilities
// ============================================

function hexToRgb(hex: string): [number, number, number] {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)]
    : [0, 0, 0];
}

function rgbToHex(r: number, g: number, b: number): string {
  return '#' + [r, g, b].map(x => Math.round(Math.max(0, Math.min(255, x))).toString(16).padStart(2, '0')).join('');
}

function rgbToHsl(r: number, g: number, b: number): [number, number, number] {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h = 0, s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
      case g: h = ((b - r) / d + 2) / 6; break;
      case b: h = ((r - g) / d + 4) / 6; break;
    }
  }
  return [h * 360, s * 100, l * 100];
}

function hslToRgb(h: number, s: number, l: number): [number, number, number] {
  h /= 360; s /= 100; l /= 100;
  let r, g, b;

  if (s === 0) {
    r = g = b = l;
  } else {
    const hue2rgb = (p: number, q: number, t: number) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }
  return [r * 255, g * 255, b * 255];
}

function interpolateColor(color1: string, color2: string, t: number): string {
  const [r1, g1, b1] = hexToRgb(color1);
  const [r2, g2, b2] = hexToRgb(color2);
  return rgbToHex(
    r1 + (r2 - r1) * t,
    g1 + (g2 - g1) * t,
    b1 + (b2 - b1) * t
  );
}

// Shift hue of a color by degrees
function shiftHue(hex: string, degrees: number): string {
  const [r, g, b] = hexToRgb(hex);
  const [h, s, l] = rgbToHsl(r, g, b);
  const newH = (h + degrees + 360) % 360;
  const [nr, ng, nb] = hslToRgb(newH, s, l);
  return rgbToHex(nr, ng, nb);
}

// Interpolate color arrays of potentially different lengths
function interpolateColorArrays(from: string[], to: string[], t: number): string[] {
  const len = to.length;
  return to.map((targetColor, i) => {
    const fromIndex = Math.floor((i / len) * from.length);
    const fromColor = from[fromIndex] || from[0];
    return interpolateColor(fromColor, targetColor, t);
  });
}

// Apply dynamic hue shift based on time - creates flowing color effect
function applyDynamicHueShift(colors: string[], time: number, intensity: number = 15): string[] {
  return colors.map((color, i) => {
    // Each color shifts with different phase for variety
    const phase = (i / colors.length) * Math.PI * 2;
    // Combine multiple sine waves for organic movement
    const shift = Math.sin(time * 0.5 + phase) * intensity
                + Math.sin(time * 0.3 + phase * 2) * (intensity * 0.5)
                + Math.cos(time * 0.7 + phase * 0.5) * (intensity * 0.3);
    return shiftHue(color, shift);
  });
}

// ============================================
// Siri Orb Component
// ============================================

function SiriOrb({ state, size }: { state: OrbState; size: number }) {
  const targetConfig = CONFIGS[state];
  const isActive = state !== 'idle';

  // Base colors (for state transitions)
  const [baseColors, setBaseColors] = useState(targetConfig.colors);
  const [currentGlow, setCurrentGlow] = useState(targetConfig.glow);

  // Dynamic colors (with hue shifting)
  const [displayColors, setDisplayColors] = useState(targetConfig.colors);

  const transitionAnimRef = useRef<number>();
  const dynamicAnimRef = useRef<number>();
  const progressRef = useRef(0);
  const timeRef = useRef(0);
  const prevColorsRef = useRef(targetConfig.colors);
  const prevGlowRef = useRef(targetConfig.glow);

  // State transition animation
  useEffect(() => {
    const startColors = [...prevColorsRef.current];
    const startGlow = prevGlowRef.current;
    const targetColors = targetConfig.colors;
    const targetGlow = targetConfig.glow;

    progressRef.current = 0;

    const animate = () => {
      progressRef.current += 0.012;
      const t = Math.min(progressRef.current, 1);
      const eased = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

      const newColors = interpolateColorArrays(startColors, targetColors, eased);
      setBaseColors(newColors);
      setCurrentGlow(interpolateColor(startGlow, targetGlow, eased));

      if (t < 1) {
        transitionAnimRef.current = requestAnimationFrame(animate);
      } else {
        prevColorsRef.current = [...targetColors];
        prevGlowRef.current = targetGlow;
      }
    };

    transitionAnimRef.current = requestAnimationFrame(animate);
    return () => {
      if (transitionAnimRef.current) cancelAnimationFrame(transitionAnimRef.current);
    };
  }, [state, targetConfig.colors, targetConfig.glow]);

  // Dynamic hue animation (continuous color flow)
  useEffect(() => {
    const animateDynamic = () => {
      timeRef.current += 0.016;

      // Apply dynamic hue shift - more intense for active states
      const intensity = isActive ? 20 : 8;
      const shifted = applyDynamicHueShift(baseColors, timeRef.current, intensity);
      setDisplayColors(shifted);

      dynamicAnimRef.current = requestAnimationFrame(animateDynamic);
    };

    dynamicAnimRef.current = requestAnimationFrame(animateDynamic);
    return () => {
      if (dynamicAnimRef.current) cancelAnimationFrame(dynamicAnimRef.current);
    };
  }, [baseColors, isActive]);

  // Generate conic gradient
  const conicGradient = useMemo(() => {
    const stops = displayColors.map((color, i) => {
      const pos = (i / displayColors.length) * 100;
      return `${color} ${pos}%`;
    });
    stops.push(`${displayColors[0]} 100%`);
    return `conic-gradient(from var(--rotation), ${stops.join(', ')})`;
  }, [displayColors]);

  return (
    <motion.div
      className={`${styles.orbContainer} ${isActive ? styles.active : ''}`}
      initial={false}
      animate={{ width: size, height: size }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      style={{
        '--size': `${size}px`,
        '--speed': `${targetConfig.speed}s`,
        '--blur': `${targetConfig.blur}px`,
        '--glow-color': currentGlow,
        '--gradient': conicGradient,
      } as React.CSSProperties}
    >
      <div className={styles.glowLayer1} />
      <div className={styles.glowLayer2} />
      <div className={styles.spinningGradient} />
      <div className={styles.innerCircle}>
        <div className={styles.innerGlow} />
      </div>
    </motion.div>
  );
}

// ============================================
// Glow Layer
// ============================================

function GlowLayer({ state, size }: { state: OrbState; size: number }) {
  const config = CONFIGS[state];

  return (
    <motion.div
      className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full pointer-events-none"
      animate={{
        scale: [1, 1.1, 1],
        opacity: [0.5, 0.7, 0.5],
      }}
      transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
      style={{
        width: size * 1.8,
        height: size * 1.8,
        background: `radial-gradient(circle, ${config.glow}40 0%, ${config.glow}15 40%, transparent 70%)`,
        filter: 'blur(20px)',
      }}
    />
  );
}

// ============================================
// Pulse Rings
// ============================================

function PulseRings({ state, size }: { state: OrbState; size: number }) {
  if (state !== 'ready') return null;
  const config = CONFIGS[state];

  return (
    <>
      <motion.div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{ width: size * 0.9, height: size * 0.9, border: `2px solid ${config.glow}` }}
        initial={{ scale: 1, opacity: 0.6 }}
        animate={{ scale: 2.5, opacity: 0 }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
      />
    </>
  );
}

// ============================================
// Message Bubble
// ============================================

function MessageBubble({
  state,
  message,
  isStreaming,
  showCursor,
  isFadingOut,
  onMouseEnter,
  onMouseLeave,
  onDismiss,
  orbSize,
}: {
  state: OrbState;
  message: string;
  isStreaming: boolean;
  showCursor: boolean;
  isFadingOut: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  onDismiss?: () => void;
  orbSize: number;
}) {
  const config = CONFIGS[state];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.9, filter: 'blur(8px)' }}
      animate={{
        opacity: isFadingOut ? 0.4 : 1,
        y: 0,
        scale: isFadingOut ? 0.97 : 1,
        filter: 'blur(0px)',
      }}
      exit={{ opacity: 0, y: 10, scale: 0.95, filter: 'blur(6px)' }}
      transition={{ type: 'spring', damping: 25, stiffness: 350 }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      className="pointer-events-auto relative"
      style={{
        background: 'rgba(10, 10, 15, 0.85)',
        backdropFilter: 'blur(40px) saturate(180%)',
        WebkitBackdropFilter: 'blur(40px) saturate(180%)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        boxShadow: `0 20px 50px rgba(0,0,0,0.5), 0 0 60px ${config.glow}20`,
        borderRadius: '22px',
      }}
    >
      {/* Use items-center for vertical centering */}
      <div className="flex items-center gap-3 px-4 py-3 max-w-md">
        <div className="flex-shrink-0 relative flex items-center justify-center" style={{ width: orbSize, height: orbSize }}>
          <SiriOrb state={state} size={orbSize} />
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.9)' }}>
            {message}
            {isStreaming && showCursor && (
              <motion.span
                className="inline-block w-0.5 h-4 ml-0.5 rounded-full align-middle"
                style={{ background: config.glow }}
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 0.8, repeat: Infinity }}
              />
            )}
          </p>
        </div>

        {onDismiss && !isStreaming && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 p-1.5 rounded-full hover:bg-white/10 transition-colors"
          >
            <X className="w-4 h-4 text-white/40" />
          </button>
        )}
      </div>
    </motion.div>
  );
}

// ============================================
// Main Component
// ============================================

export function NeuralOrb({
  state,
  visible = true,
  message,
  isStreaming = false,
  onDismiss,
  autoDismissDelay = 15000,
}: NeuralOrbProps) {
  const [showCursor, setShowCursor] = useState(true);
  const [isHovered, setIsHovered] = useState(false);
  const [isFadingOut, setIsFadingOut] = useState(false);
  const fadeTimerRef = useRef<NodeJS.Timeout | null>(null);
  const dismissTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!isStreaming) {
      setShowCursor(false);
      return;
    }
    const interval = setInterval(() => setShowCursor((v) => !v), 500);
    return () => clearInterval(interval);
  }, [isStreaming]);

  useEffect(() => {
    const showMessage = state === 'speaking' && message;

    if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current);
    if (dismissTimerRef.current) clearTimeout(dismissTimerRef.current);

    if (showMessage && !isStreaming && !isHovered && onDismiss) {
      fadeTimerRef.current = setTimeout(() => setIsFadingOut(true), autoDismissDelay - 800);
      dismissTimerRef.current = setTimeout(() => {
        setIsFadingOut(false);
        onDismiss();
      }, autoDismissDelay);
    } else {
      setIsFadingOut(false);
    }

    return () => {
      if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current);
      if (dismissTimerRef.current) clearTimeout(dismissTimerRef.current);
    };
  }, [state, message, isStreaming, isHovered, onDismiss, autoDismissDelay]);

  useEffect(() => {
    setIsFadingOut(false);
  }, [message]);

  if (!visible) return null;

  const showMessage = state === 'speaking' && message;

  // Use consistent size across all states - based on speaking state size
  const orbSize = 48;

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-40 pointer-events-none">
      <AnimatePresence mode="wait">
        {showMessage ? (
          <motion.div key="bubble" className="flex flex-col items-center">
            <MessageBubble
              state={state}
              message={message}
              isStreaming={isStreaming}
              showCursor={showCursor}
              isFadingOut={isFadingOut}
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
              onDismiss={onDismiss}
              orbSize={orbSize}
            />
          </motion.div>
        ) : (
          <motion.div
            key="orb"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            className="relative flex items-center justify-center"
            style={{ width: orbSize * 2, height: orbSize * 2 }}
          >
            <GlowLayer state={state} size={orbSize} />
            <PulseRings state={state} size={orbSize} />
            <SiriOrb state={state} size={orbSize} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default NeuralOrb;
