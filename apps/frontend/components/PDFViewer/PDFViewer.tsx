'use client';

import React, { useState, useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Loader2, ZoomIn, ZoomOut } from 'lucide-react';

import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Set up PDF.js worker for v7
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

export interface PDFViewerProps {
  fileUrl: string;
  onTextSelect?: (selectedText: string) => void;
  onPageClick?: () => void;
  onScroll?: (scrollTop: number) => void;
  /** 回调方式获取容器和文本（用于凝视检测） */
  onContainerReady?: (container: HTMLDivElement, getVisibleText: () => string) => void;
}

// Ref handle for external access
export interface PDFViewerHandle {
  getScrollContainer: () => HTMLDivElement | null;
  getVisibleHeight: () => number;
  getTotalHeight: () => number;
  getTextAtPosition: (scrollY: number) => string;
}

const PDFViewer = forwardRef<PDFViewerHandle, PDFViewerProps>(function PDFViewer(
  { fileUrl, onTextSelect, onPageClick, onScroll, onContainerReady },
  ref
) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [scale, setScale] = useState(1.2);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const selectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    getScrollContainer: () => containerRef.current,
    getVisibleHeight: () => containerRef.current?.clientHeight || 0,
    getTotalHeight: () => containerRef.current?.scrollHeight || 0,
    getTextAtPosition: (scrollY: number) => {
      const container = containerRef.current;
      if (!container) return '';

      // Find the page at the given scroll position
      const pages = container.querySelectorAll('.pdf-page-wrapper');
      for (const page of pages) {
        const rect = page.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        const relativeTop = rect.top - containerRect.top + container.scrollTop;
        const relativeBottom = relativeTop + rect.height;

        if (scrollY >= relativeTop && scrollY <= relativeBottom) {
          const textLayer = page.querySelector('.textLayer, .react-pdf__Page__textContent');
          return textLayer?.textContent?.trim()?.substring(0, 500) || '';
        }
      }

      // Fallback: get text from center of viewport
      const viewportCenter = container.clientHeight / 2;
      for (const page of pages) {
        const rect = page.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        const pageCenter = rect.top - containerRect.top + rect.height / 2;

        if (Math.abs(pageCenter - viewportCenter) < rect.height / 2) {
          const textLayer = page.querySelector('.textLayer, .react-pdf__Page__textContent');
          return textLayer?.textContent?.trim()?.substring(0, 500) || '';
        }
      }

      return '';
    },
  }), []);

  // Handle document load success
  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setError(null);
  }, []);

  // Handle document load error
  const onDocumentLoadError = useCallback((err: Error) => {
    console.error('PDF load error:', err);
    setError(`Failed to load PDF: ${err.message}`);
  }, []);

  // Handle text selection
  useEffect(() => {
    const handleMouseUp = () => {
      if (selectionTimeoutRef.current) {
        clearTimeout(selectionTimeoutRef.current);
      }

      selectionTimeoutRef.current = setTimeout(() => {
        const selection = window.getSelection();
        if (!selection || selection.isCollapsed) return;

        const text = selection.toString().trim();
        if (text && text.length >= 15 && onTextSelect) {
          onTextSelect(text);
        }
      }, 300);
    };

    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
      if (selectionTimeoutRef.current) {
        clearTimeout(selectionTimeoutRef.current);
      }
    };
  }, [onTextSelect]);

  // Handle scroll for backtrack detection
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !onScroll) return;

    const handleScroll = () => {
      onScroll(container.scrollTop);
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, [onScroll]);

  // Zoom controls
  const zoomIn = useCallback(() => setScale(s => Math.min(s + 0.2, 3.0)), []);
  const zoomOut = useCallback(() => setScale(s => Math.max(s - 0.2, 0.5)), []);

  // 通知父组件容器已就绪
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !onContainerReady) return;

    const getVisibleText = () => {
      const viewportCenter = container.scrollTop + container.clientHeight / 2;
      const pages = container.querySelectorAll('.pdf-page-wrapper');

      for (const page of pages) {
        const rect = page.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        const pageCenter = rect.top - containerRect.top + container.scrollTop + rect.height / 2;

        if (Math.abs(pageCenter - viewportCenter) < rect.height / 2) {
          const textLayer = page.querySelector('.textLayer, .react-pdf__Page__textContent');
          return textLayer?.textContent?.trim()?.substring(0, 500) || '';
        }
      }
      return '';
    };

    // 延迟一下确保 DOM 已渲染
    const timer = setTimeout(() => {
      onContainerReady(container, getVisibleText);
    }, 100);

    return () => clearTimeout(timer);
  }, [onContainerReady, numPages]); // numPages 变化说明内容加载完成

  return (
    <div className="h-full flex flex-col bg-[var(--bg-primary)]" onClick={onPageClick}>
      {/* Controls */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[rgba(255,255,255,0.05)] bg-[var(--bg-secondary)]">
        <div className="text-sm text-[var(--text-muted)]">
          {numPages ? `${numPages} pages` : 'Loading...'}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); zoomOut(); }}
            disabled={scale <= 0.5}
            className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] disabled:opacity-30 transition-colors"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-sm text-[var(--text-secondary)] w-14 text-center tabular-nums">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={(e) => { e.stopPropagation(); zoomIn(); }}
            disabled={scale >= 3.0}
            className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] disabled:opacity-30 transition-colors"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* PDF Container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto pdf-scroll-container"
      >
        {error ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-[var(--error)] mb-2">{error}</p>
              <p className="text-sm text-[var(--text-muted)]">Please try refreshing the page</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center py-6 px-4">
            <Document
              file={fileUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <div className="flex items-center gap-3 text-[var(--text-muted)]">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Loading PDF...</span>
                </div>
              }
              className="pdf-document"
            >
              {numPages && Array.from({ length: numPages }, (_, i) => i + 1).map((pageNum) => (
                <div key={pageNum} className="mb-4 pdf-page-wrapper" data-page-number={pageNum}>
                  <Page
                    pageNumber={pageNum}
                    scale={scale}
                    renderTextLayer={true}
                    renderAnnotationLayer={true}
                    className="pdf-page"
                    loading={
                      <div className="flex items-center justify-center h-[800px] bg-[var(--bg-tertiary)] rounded">
                        <Loader2 className="w-5 h-5 animate-spin text-[var(--text-muted)]" />
                      </div>
                    }
                  />
                </div>
              ))}
            </Document>
          </div>
        )}
      </div>
    </div>
  );
});

export default PDFViewer;
