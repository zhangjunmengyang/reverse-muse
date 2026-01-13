'use client';

import React, { useEffect, useState } from 'react';
import { Sparkles, X } from 'lucide-react';

interface Insight {
  id: string;
  content: string;
  insight_type: string;
  confidence: number;
}

interface BubbleInsightProps {
  insight: Insight | null;
  position?: { x: number; y: number };
  onDismiss?: () => void;
  onPin?: () => void;
}

export default function BubbleInsight({ insight, position, onDismiss, onPin }: BubbleInsightProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (insight) {
      setVisible(true);
    }
  }, [insight]);

  if (!insight || !visible) {
    return null;
  }

  return (
    <div
      className="fixed bubble-enter z-50"
      style={{
        left: position?.x || 50,
        top: position?.y || 100,
      }}
    >
      <div className="relative">
        {/* Bubble Arrow */}
        <div
          className="absolute -top-2 left-1/2 transform -translate-x-1/2 w-4 h-4 bg-blue-500 rotate-45"
        ></div>

        {/* Bubble Content */}
        <div
          className="bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-2xl shadow-2xl p-5 min-w-[300px] max-w-[400px]"
        >
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-5 h-5" />
              <span className="text-sm font-semibold opacity-90">
                {insight.insight_type.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center space-x-1">
              <button
                onClick={onPin}
                className="p-1 hover:bg-white/20 rounded transition-colors"
                title="Pin insight"
              >
                <span className="text-xs">📌</span>
              </button>
              <button
                onClick={() => {
                  setVisible(false);
                  onDismiss?.();
                }}
                className="p-1 hover:bg-white/20 rounded transition-colors"
                title="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Content */}
          <p className="text-sm leading-relaxed opacity-95 mb-4">
            {insight.content}
          </p>

          {/* Confidence Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs opacity-75">
              <span>Confidence</span>
              <span>{Math.round(insight.confidence * 100)}%</span>
            </div>
            <div className="h-1.5 bg-white/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-white rounded-full transition-all duration-500"
                style={{ width: `${insight.confidence * 100}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Glow Effect */}
        <div className="absolute inset-0 -m-2 rounded-3xl bg-blue-500/20 blur-xl -z-10"></div>
      </div>
    </div>
  );
}
