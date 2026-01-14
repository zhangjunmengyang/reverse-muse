'use client';

import React, { useState, useEffect, useCallback, useRef, Suspense, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import {
  Ghost,
  FileText,
  Loader2,
  Search,
  X,
  Clock,
  ArrowLeft,
  Upload,
  Plus,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';

import { api } from '@/lib/api';
import type { Paper, Insight } from '@/lib/types';
import { NeuralOrb } from '@/components/NeuralOrb';
import { useGazeDetection, type GazeState } from '@/hooks/useGazeDetection';

// Dynamically import PDF viewer to avoid SSR issues with canvas
const PDFViewer = dynamic(() => import('@/components/PDFViewer'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center">
      <Loader2 className="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
    </div>
  ),
});

// Ghost Bubble State Types
type BubbleState = 'hidden' | 'sensing' | 'ready' | 'engaged';

interface GhostBubbleState {
  state: BubbleState;
  insight: Insight | null;
  selectedText: string;
  isStreaming: boolean;
  triggerType: 'selection' | 'linger' | 'backtrack';
}

// Main page component wrapped with Suspense
export default function ReadingPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <ReadingPageContent />
    </Suspense>
  );
}

function LoadingFallback() {
  return (
    <div className="h-screen flex items-center justify-center bg-[var(--bg-primary)]">
      <Loader2 className="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
    </div>
  );
}

function ReadingPageContent() {
  const searchParams = useSearchParams();
  const showUploadOnMount = searchParams?.get('upload') === 'true';
  const showDebug = searchParams?.get('debug') === 'true';

  // State
  const [papers, setPapers] = useState<Paper[]>([]);
  const [filteredPapers, setFilteredPapers] = useState<Paper[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [contextId, setContextId] = useState<string>('');
  const [recentInsights, setRecentInsights] = useState<Insight[]>([]);

  // Ghost Bubble state
  const [bubble, setBubble] = useState<GhostBubbleState>({
    state: 'hidden',
    insight: null,
    selectedText: '',
    isStreaming: false,
    triggerType: 'selection',
  });
  const [streamedContent, setStreamedContent] = useState('');

  // Upload state
  const [showUploadModal, setShowUploadModal] = useState(showUploadOnMount);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Loading states
  const [loadingLibrary, setLoadingLibrary] = useState(true);
  const [loadingPaper, setLoadingPaper] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Session
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const userId = 'demo_user';

  // Refs
  const dismissTimerRef = useRef<NodeJS.Timeout | null>(null);
  const scrollContainerRef = useRef<HTMLElement | null>(null);
  const mainContentRef = useRef<HTMLDivElement>(null);
  const selectionIntentRef = useRef<{
    timestamp: number;
    copied: boolean;
    rightClicked: boolean;
  }>({
    timestamp: 0,
    copied: false,
    rightClicked: false,
  });

  // ============================================
  // 凝视检测 (Gaze Detection)
  // 简化逻辑：5秒无活动 -> observing, 8秒无活动 -> ready -> 触发洞察
  // ============================================

  // 存储获取文本的函数
  const getVisibleTextRef = useRef<() => string>(() => '');

  // 获取当前可见文本的配置
  const gazeConfig = useMemo(() => ({
    getVisibleText: () => getVisibleTextRef.current(),
  }), []);

  // 凝视检测 hook
  const gazeDetection = useGazeDetection(scrollContainerRef, gazeConfig);

  // 凝视触发洞察
  const lastGazeStateRef = useRef<GazeState>('idle');

  useEffect(() => {
    const { state, stateJustChanged, focusedText } = gazeDetection;

    // Debug 日志
    if (stateJustChanged) {
      console.log('[Gaze] 状态变化:', lastGazeStateRef.current, '->', state, 'focusedText:', focusedText.substring(0, 50));
    }

    // 状态变为 ready 时触发洞察
    if (stateJustChanged && state === 'ready' && lastGazeStateRef.current !== 'ready') {
      console.log('[Gaze] Ready 状态触发! contextId:', contextId, 'textLen:', focusedText.length);
      if (contextId && focusedText.length > 30) {
        console.log('[Gaze] 调用 triggerInsight...');
        triggerInsightRef.current(focusedText, 'linger');
      } else {
        console.log('[Gaze] 条件不满足 - contextId:', !!contextId, 'textLen:', focusedText.length);
      }
    }

    lastGazeStateRef.current = state;
  }, [gazeDetection.state, gazeDetection.stateJustChanged, gazeDetection.focusedText, contextId]);

  // PDF 容器就绪回调
  const handleContainerReady = useCallback((container: HTMLDivElement, getVisibleText: () => string) => {
    scrollContainerRef.current = container;
    getVisibleTextRef.current = getVisibleText;
  }, []);

  // ============================================
  // Library & Paper Management
  // ============================================

  // Load paper library
  useEffect(() => {
    loadLibrary(true);
  }, []);

  const loadLibrary = async (autoSelectFirst: boolean = false) => {
    setLoadingLibrary(true);
    setLoadError(null);
    try {
      const data = await api.getLibrary();
      setPapers(data.papers);
      setFilteredPapers(data.papers);

      // Auto-select first paper on initial load
      if (autoSelectFirst && data.papers.length > 0 && !selectedPaper) {
        handleSelectPaper(data.papers[0]);
      }
    } catch {
      setLoadError('Failed to load paper library');
    } finally {
      setLoadingLibrary(false);
    }
  };

  // Filter papers by search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredPapers(papers);
    } else {
      const query = searchQuery.toLowerCase();
      setFilteredPapers(
        papers.filter(
          (p) =>
            p.title.toLowerCase().includes(query) ||
            p.paper_id.includes(query) ||
            p.author?.toLowerCase().includes(query)
        )
      );
    }
  }, [searchQuery, papers]);

  // ============================================
  // Selection Intent Detection
  // ============================================

  // Listen for copy events
  useEffect(() => {
    const handleCopy = () => {
      selectionIntentRef.current.copied = true;
    };
    document.addEventListener('copy', handleCopy);
    return () => document.removeEventListener('copy', handleCopy);
  }, []);

  // Listen for right-click (context menu)
  useEffect(() => {
    const handleContextMenu = () => {
      const selection = window.getSelection();
      if (selection && !selection.isCollapsed) {
        selectionIntentRef.current.rightClicked = true;
      }
    };
    document.addEventListener('contextmenu', handleContextMenu);
    return () => document.removeEventListener('contextmenu', handleContextMenu);
  }, []);

  // Listen for Ctrl/Cmd+C
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
        selectionIntentRef.current.copied = true;
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // ============================================
  // File Upload
  // ============================================

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setUploadError('Please select a PDF file');
        return;
      }
      setUploadFile(file);
      setUploadError(null);
      setUploadSuccess(null);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) return;
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);
    try {
      const result = await api.uploadPaper(uploadFile, userId);
      setUploadSuccess(`Uploaded "${result.filename}" (${result.page_count} pages)`);
      setUploadFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await loadLibrary();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      setUploadError(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  // ============================================
  // Paper Selection & Session
  // ============================================

  const handleSelectPaper = async (paper: Paper) => {
    setSelectedPaper(paper);
    setLoadingPaper(true);
    setBubble({ state: 'hidden', insight: null, selectedText: '', isStreaming: false, triggerType: 'selection' });
    scrollContainerRef.current = null;

    try {
      await api.loadPaper(paper.paper_id, userId);
      const session = await api.startSession(userId, paper.paper_id, sessionId);
      setContextId(session.context_id);
    } catch {
      // Paper loading failed, user can retry
    } finally {
      setLoadingPaper(false);
    }
  };

  // ============================================
  // Insight Generation
  // ============================================

  const streamText = useCallback((fullText: string) => {
    setStreamedContent('');
    setBubble(prev => ({ ...prev, isStreaming: true }));

    let index = 0;
    const interval = setInterval(() => {
      if (index < fullText.length) {
        setStreamedContent(fullText.substring(0, index + 1));
        index++;
      } else {
        clearInterval(interval);
        setBubble(prev => ({ ...prev, isStreaming: false }));
      }
    }, 30); // 更慢的流式输出，增加阅读舒适度

    return () => clearInterval(interval);
  }, []);

  const triggerInsight = useCallback(async (
    text: string,
    triggerType: 'selection' | 'linger' | 'backtrack',
    pageNumber: number = 1
  ) => {
    console.log('[Insight] triggerInsight 被调用:', { triggerType, textLen: text?.length, contextId, bubbleState: bubble.state });

    if (!text || text.length < 10 || !contextId) {
      console.log('[Insight] 提前返回: text 或 contextId 不满足');
      return;
    }
    if (bubble.state === 'sensing' || bubble.state === 'engaged') {
      console.log('[Insight] 提前返回: bubble 状态不允许', bubble.state);
      return;
    }

    if (dismissTimerRef.current) {
      clearTimeout(dismissTimerRef.current);
    }

    console.log('[Insight] 设置 sensing 状态...');
    setBubble({
      state: 'sensing',
      insight: null,
      selectedText: text,
      isStreaming: false,
      triggerType,
    });

    try {
      console.log('[Insight] 调用 API...');
      const response = await api.recordAction(contextId, {
        trigger_type: triggerType,
        selected_text: text,
        context_text: text.substring(0, 500),
        reading_position: {
          paper_id: selectedPaper?.paper_id || '',
          page_number: pageNumber,
          text_snippet: text.substring(0, 100),
        },
      });

      console.log('[Insight] API 响应:', { hasInsight: !!response.insight, insight: response.insight?.content?.substring(0, 50) });

      if (response.insight) {
        console.log('[Insight] 设置 engaged 状态，开始流式输出');
        setBubble({
          state: 'engaged',
          insight: response.insight,
          selectedText: text,
          isStreaming: true,
          triggerType,
        });

        streamText(response.insight.content);
        setRecentInsights(prev => [response.insight!, ...prev].slice(0, 10));

        // 自动消失由 NeuralOrb 组件内部控制（支持悬浮暂停）
        // 这里不再设置定时器
      } else {
        // AI decided to stay silent
        console.log('[Insight] API 返回无洞察，隐藏气泡');
        setTimeout(() => {
          setBubble({ state: 'hidden', insight: null, selectedText: '', isStreaming: false, triggerType: 'selection' });
        }, 300);
      }
    } catch (err) {
      console.error('[Insight] API 错误:', err);
      setBubble({ state: 'hidden', insight: null, selectedText: '', isStreaming: false, triggerType: 'selection' });
    }
  }, [contextId, selectedPaper, bubble.state, streamText]);

  // Store triggerInsight in ref for NeuralOrb callback
  const triggerInsightRef = useRef(triggerInsight);
  triggerInsightRef.current = triggerInsight;

  // ============================================
  // Text Selection Handler (with intent detection)
  // ============================================

  const handleTextSelection = useCallback(async (selectedText: string) => {
    console.log('[Selection] 文本选中:', selectedText?.substring(0, 30), 'len:', selectedText?.length, 'contextId:', contextId);

    if (!selectedText || selectedText.length < 15 || !contextId) {
      console.log('[Selection] 提前返回: 条件不满足');
      return;
    }

    selectionIntentRef.current = {
      timestamp: Date.now(),
      copied: false,
      rightClicked: false,
    };

    // Wait 1 second to check intent
    setTimeout(() => {
      const intent = selectionIntentRef.current;
      console.log('[Selection] 1秒后检查意图:', intent);

      // Skip if user copied or right-clicked (indicates different intent)
      if (intent.copied || intent.rightClicked) {
        console.log('[Selection] 用户复制或右键，跳过');
        return;
      }

      // Check if selection is still active (use trim and normalize for comparison)
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) {
        console.log('[Selection] 选区已消失，跳过');
        return;
      }

      // Normalize both texts for comparison (handle whitespace differences)
      const currentText = selection.toString().trim().replace(/\s+/g, ' ');
      const originalText = selectedText.trim().replace(/\s+/g, ' ');

      // Allow if the text is similar enough (contains most of the original)
      if (currentText.length < 10 || !currentText.includes(originalText.substring(0, Math.min(50, originalText.length)))) {
        console.log('[Selection] 选区已变化，跳过', { currentLen: currentText.length, originalLen: originalText.length });
        return;
      }

      console.log('[Selection] 条件满足，触发 insight');

      triggerInsightRef.current(selectedText, 'selection');
    }, 1000);
  }, [contextId]);

  // ============================================
  // Cleanup timer on unmount
  // ============================================

  useEffect(() => {
    return () => {
      if (dismissTimerRef.current) {
        clearTimeout(dismissTimerRef.current);
      }
    };
  }, []);

  // ============================================
  // Bubble Dismiss
  // ============================================

  const dismissBubble = useCallback(() => {
    if (dismissTimerRef.current) {
      clearTimeout(dismissTimerRef.current);
    }
    setBubble({ state: 'hidden', insight: null, selectedText: '', isStreaming: false, triggerType: 'selection' });
  }, []);

  // ============================================
  // Render
  // ============================================

  return (
    <div className="h-screen flex overflow-hidden bg-[var(--bg-primary)]">

      {/* Debug Overlay - 简化版 */}
      {showDebug && (
        <div className="fixed bottom-4 right-4 z-50 p-3 rounded-lg bg-black/80 text-white text-xs font-mono">
          <div>State: <span className="text-green-400">{gazeDetection.state}</span></div>
          <div>Gaze: {(gazeDetection.gazeTime / 1000).toFixed(1)}s</div>
        </div>
      )}

      {/* 移除旧的 GhostBubble，使用 NeuralOrb 的底部悬浮条 */}

      {/* Sidebar */}
      <aside className="w-72 flex-shrink-0 bg-[var(--bg-secondary)] border-r border-[rgba(255,255,255,0.05)] flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-[rgba(255,255,255,0.05)]">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Home</span>
          </Link>

          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[var(--ghost-bg)] border border-[var(--ghost-border)] flex items-center justify-center">
              <Ghost className="w-4 h-4 text-[var(--accent-secondary)]" />
            </div>
            <div>
              <h1 className="font-display text-base font-semibold text-gradient">
                Reverse Muse
              </h1>
              <p className="text-xs text-[var(--text-muted)]">Silent observer mode</p>
            </div>
          </div>
        </div>

        {/* Search & Upload */}
        <div className="p-3 border-b border-[rgba(255,255,255,0.05)] space-y-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
            <input
              type="text"
              placeholder="Search papers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input w-full pl-10 pr-10 py-2 text-sm"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <button
            onClick={() => setShowUploadModal(true)}
            className="w-full btn btn-ghost text-sm py-2"
          >
            <Plus className="w-4 h-4" />
            <span>Upload Paper</span>
          </button>
        </div>

        {/* Paper List */}
        <div className="flex-1 overflow-y-auto p-3">
          <h3 className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider mb-2">
            Library ({filteredPapers.length})
          </h3>

          {loadingLibrary ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="p-2 rounded-lg">
                  <div className="skeleton h-4 w-3/4 mb-1" />
                  <div className="skeleton h-3 w-1/2" />
                </div>
              ))}
            </div>
          ) : loadError ? (
            <div className="text-center py-6">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 text-[var(--error)] opacity-70" />
              <p className="text-xs text-[var(--text-muted)] mb-3">{loadError}</p>
              <button onClick={() => loadLibrary()} className="btn btn-ghost text-xs py-1.5">
                Retry
              </button>
            </div>
          ) : filteredPapers.length === 0 ? (
            <div className="text-center py-6 text-[var(--text-muted)]">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-xs mb-3">
                {papers.length === 0 ? 'No papers yet' : 'No matches'}
              </p>
              {papers.length === 0 && (
                <button onClick={() => setShowUploadModal(true)} className="btn btn-ghost text-xs py-1.5">
                  <Upload className="w-3 h-3" />
                  Upload first paper
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-1">
              {filteredPapers.map((paper) => (
                <button
                  key={paper.paper_id}
                  onClick={() => handleSelectPaper(paper)}
                  disabled={loadingPaper}
                  className={`
                    w-full text-left p-2 rounded-lg transition-all text-sm
                    ${selectedPaper?.paper_id === paper.paper_id
                      ? 'bg-[var(--ghost-bg)] border border-[var(--ghost-border)]'
                      : 'hover:bg-[var(--bg-tertiary)] border border-transparent'
                    }
                  `}
                >
                  <div className="flex items-start gap-2">
                    <FileText
                      className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${
                        selectedPaper?.paper_id === paper.paper_id
                          ? 'text-[var(--accent-secondary)]'
                          : 'text-[var(--text-muted)]'
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-medium text-[var(--text-primary)] line-clamp-2">
                        {paper.title || paper.paper_id}
                      </div>
                      <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
                        {paper.page_count} pages
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Recent Insights */}
        {recentInsights.length > 0 && (
          <div className="border-t border-[rgba(255,255,255,0.05)] p-3 max-h-48 overflow-y-auto">
            <h3 className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Clock className="w-3 h-3" />
              Recent
            </h3>
            <div className="space-y-1.5">
              {recentInsights.slice(0, 3).map((insight, index) => (
                <div
                  key={insight.id || index}
                  className="p-2 rounded-lg bg-[var(--bg-tertiary)] text-xs"
                >
                  <div className="text-[10px] text-[var(--accent-secondary)] font-medium mb-0.5">
                    {insight.insight_type}
                  </div>
                  <div className="text-[var(--text-secondary)] line-clamp-2 text-[11px]">
                    {insight.content}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </aside>

      {/* Main Content - PDF Viewer */}
      <main ref={mainContentRef} className="flex-1 flex flex-col min-w-0 relative">
        {!selectedPaper ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-sm">
              <div className="w-16 h-16 rounded-2xl bg-[var(--ghost-bg)] border border-[var(--ghost-border)] flex items-center justify-center mx-auto mb-5 animate-ghost-float">
                <Ghost className="w-8 h-8 text-[var(--accent-secondary)]" />
              </div>
              <h2 className="font-display text-xl font-semibold mb-2">
                Select a paper
              </h2>
              <p className="text-sm text-[var(--text-secondary)] mb-5">
                Choose from library or upload. I&apos;ll observe silently and only speak when truly helpful.
              </p>
              <button onClick={() => setShowUploadModal(true)} className="btn btn-primary text-sm">
                <Upload className="w-4 h-4" />
                Upload Paper
              </button>
            </div>
          </div>
        ) : loadingPaper ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-[var(--accent-primary)] animate-spin mx-auto mb-3" />
              <p className="text-sm text-[var(--text-secondary)]">Loading paper...</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-hidden relative">
            {/* NeuralOrb - 论文区底部中央 */}
            <NeuralOrb
              state={
                // 优先级: sensing(思考中) > engaged(说话) > gazeDetection 状态
                bubble.state === 'sensing' ? 'observing' :
                bubble.state === 'engaged' || bubble.isStreaming ? 'speaking' :
                gazeDetection.state
              }
              visible={true}
              message={bubble.state === 'engaged' ? (bubble.isStreaming ? streamedContent : bubble.insight?.content) : undefined}
              isStreaming={bubble.isStreaming}
              onDismiss={dismissBubble}
            />
            <PDFViewer
              fileUrl={api.getPdfUrl(selectedPaper.paper_id)}
              onTextSelect={handleTextSelection}
              onPageClick={dismissBubble}
              onContainerReady={handleContainerReady}
            />
          </div>
        )}
      </main>

      {/* Upload Modal */}
      {showUploadModal && (
        <UploadModal
          uploadFile={uploadFile}
          uploading={uploading}
          uploadError={uploadError}
          uploadSuccess={uploadSuccess}
          fileInputRef={fileInputRef}
          onFileSelect={handleFileSelect}
          onUpload={handleUpload}
          onClose={() => {
            if (!uploading) {
              setShowUploadModal(false);
              setUploadFile(null);
              setUploadError(null);
              setUploadSuccess(null);
            }
          }}
        />
      )}
    </div>
  );
}

// ============================================
// Upload Modal Component
// ============================================

function UploadModal({
  uploadFile,
  uploading,
  uploadError,
  uploadSuccess,
  fileInputRef,
  onFileSelect,
  onUpload,
  onClose,
}: {
  uploadFile: File | null;
  uploading: boolean;
  uploadError: string | null;
  uploadSuccess: string | null;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onUpload: () => void;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md mx-4 glass rounded-2xl p-5 animate-slide-up">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          disabled={uploading}
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-xl bg-[var(--ghost-bg)] border border-[var(--ghost-border)] flex items-center justify-center">
            <Upload className="w-4 h-4 text-[var(--accent-secondary)]" />
          </div>
          <div>
            <h2 className="font-display text-base font-semibold">Upload Paper</h2>
            <p className="text-xs text-[var(--text-muted)]">PDF files, max 50MB</p>
          </div>
        </div>

        <div className="mb-4">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={onFileSelect}
            className="hidden"
            id="pdf-upload"
            disabled={uploading}
          />
          <label
            htmlFor="pdf-upload"
            className={`
              block w-full p-5 border-2 border-dashed rounded-xl text-center cursor-pointer transition-colors
              ${uploadFile
                ? 'border-[var(--accent-primary)] bg-[var(--ghost-bg)]'
                : 'border-[rgba(255,255,255,0.1)] hover:border-[var(--accent-primary)] hover:bg-[var(--ghost-bg)]'
              }
              ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
            `}
          >
            {uploadFile ? (
              <div className="flex items-center justify-center gap-2">
                <FileText className="w-4 h-4 text-[var(--accent-secondary)]" />
                <span className="text-sm text-[var(--text-primary)]">{uploadFile.name}</span>
              </div>
            ) : (
              <div>
                <Upload className="w-6 h-6 text-[var(--text-muted)] mx-auto mb-1.5" />
                <p className="text-sm text-[var(--text-secondary)]">Click to select</p>
              </div>
            )}
          </label>
        </div>

        {uploadError && (
          <div className="mb-3 p-2.5 rounded-lg bg-[var(--error)]/10 border border-[var(--error)]/30 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-[var(--error)]" />
            <span className="text-xs text-[var(--error)]">{uploadError}</span>
          </div>
        )}

        {uploadSuccess && (
          <div className="mb-3 p-2.5 rounded-lg bg-[var(--success)]/10 border border-[var(--success)]/30 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-[var(--success)]" />
            <span className="text-xs text-[var(--success)]">{uploadSuccess}</span>
          </div>
        )}

        <button
          onClick={onUpload}
          disabled={!uploadFile || uploading}
          className="w-full btn btn-primary py-2.5 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Uploading...</span>
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              <span>Upload</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
