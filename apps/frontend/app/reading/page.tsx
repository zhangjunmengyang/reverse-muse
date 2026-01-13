'use client';

import React, { useState, useEffect } from 'react';
import PDFViewer from '@/components/pdf-viewer/PDFViewer';
import BubbleInsight from '@/components/bubble-insight/BubbleInsight';
import axios from 'axios';
import { Brain, Loader2 } from 'lucide-react';

interface Insight {
  id: string;
  content: string;
  insight_type: string;
  confidence: number;
}

export default function ReadingPage() {
  const [contextId, setContextId] = useState<string>('');
  const [currentInsight, setCurrentInsight] = useState<Insight | null>(null);
  const [bubblePosition, setBubblePosition] = useState<{ x: number; y: number }>({ x: 100, y: 200 });
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const paperId = 'demo_paper_001';

  // Start reading session
  useEffect(() => {
    const startSession = async () => {
      try {
        const response = await axios.post('http://127.0.0.1:8000/api/v1/reading/start', {
          user_id: 'demo_user',
          paper_id: paperId,
          session_id: sessionId,
        });
        setContextId(response.data.context_id);
        console.log('Reading session started:', response.data);
      } catch (error) {
        console.error('Failed to start session:', error);
      }
    };
    startSession();
  }, []);

  // Handle text selection
  const handleTextSelect = async (text: string, position: any) => {
    console.log('Text selected:', text);

    setIsLoading(true);
    try {
      const response = await axios.post(
        `http://127.0.0.1:8000/api/v1/reading/action?context_id=${contextId}`,
        {
          trigger_type: 'selection',
          selected_text: text,
          context_text: text.substring(0, 200),
          reading_position: position,
          duration_seconds: null,
        }
      );

      if (response.data.insight) {
        setCurrentInsight(response.data.insight);
        // Random position for demo
        setBubblePosition({
          x: Math.random() * 60 + 20,
          y: Math.random() * 40 + 20,
        });
        console.log('Insight generated:', response.data.insight);
      }
    } catch (error) {
      console.error('Failed to record action:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDismissInsight = () => {
    setCurrentInsight(null);
  };

  const handlePageChange = async (pageNumber: number) => {
    console.log('Page changed to:', pageNumber);
    // Record linger trigger
    try {
      await axios.post(
        `http://127.0.0.1:8000/api/v1/reading/action?context_id=${contextId}`,
        {
          trigger_type: 'scroll_stop',
          selected_text: null,
          context_text: null,
          reading_position: {
            paper_id: paperId,
            page_number: pageNumber,
          },
          duration_seconds: 5,
        }
      );
    } catch (error) {
      console.error('Failed to record action:', error);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center space-x-2 mb-2">
            <Brain className="w-8 h-8 text-primary-600" />
            <h1 className="text-xl font-bold text-gray-900">Reverse Muse</h1>
          </div>
          <p className="text-sm text-gray-600">
            AI-Powered Reading Companion
          </p>
        </div>

        <div className="flex-1 p-4 space-y-4">
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              Session Info
            </h3>
            <div className="text-sm space-y-1">
              <div className="flex justify-between">
                <span className="text-gray-600">Paper:</span>
                <span className="font-medium text-gray-900">
                  Demo Paper
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Session:</span>
                <span className="font-medium text-gray-900">
                  {sessionId.slice(-8)}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Recent Insights
          </h3>
          <div className="text-sm text-gray-500 italic">
            No insights yet...
          </div>
        </div>
      </div>

      {/* Main Content - PDF Viewer */}
      <div className="flex-1 relative">
        <PDFViewer
          paperId={paperId}
          onTextSelect={handleTextSelect}
          onPageChange={handlePageChange}
        />

        {/* Loading Indicator */}
        {isLoading && (
          <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg px-4 py-2 flex items-center space-x-2">
            <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
            <span className="text-sm text-gray-700">Thinking...</span>
          </div>
        )}

         {/* AI Bubble Insight */}
        {currentInsight && (
          <BubbleInsight
            insight={currentInsight}
            position={bubblePosition}
            onDismiss={handleDismissInsight}
          />
        )}
      </div>
    </div>
  );
}
