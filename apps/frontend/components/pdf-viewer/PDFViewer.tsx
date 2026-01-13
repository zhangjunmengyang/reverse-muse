'use client';

import React, { useRef, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PDFViewerProps {
  paperId: string;
  pdfUrl?: string;
  onTextSelect?: (text: string, position: any) => void;
  onPageChange?: (pageNumber: number) => void;
}

export default function PDFViewer({ paperId, pdfUrl, onTextSelect, onPageChange }: PDFViewerProps) {
  const [pageNumber, setPageNumber] = useState(1);
  const [totalPages, setTotalPages] = useState(10); // Mock data
  const [selectedText, setSelectedText] = useState('');
  const selectionRef = useRef<HTMLDivElement>(null);

  const handleTextSelection = () => {
    const selection = window.getSelection();
    if (selection && selection.toString().trim()) {
      const text = selection.toString();
      setSelectedText(text);
      if (onTextSelect && selection.anchorOffset >= 0) {
        onTextSelect(text, {
          paperId,
          page_number: pageNumber,
          text_snippet: text.substring(0, 100),
        });
      }
    }
  };

  const handlePreviousPage = () => {
    if (pageNumber > 1) {
      const newPage = pageNumber - 1;
      setPageNumber(newPage);
      onPageChange?.(newPage);
    }
  };

  const handleNextPage = () => {
    if (pageNumber < totalPages) {
      const newPage = pageNumber + 1;
      setPageNumber(newPage);
      onPageChange?.(newPage);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-screen bg-gray-100">
      {/* PDF Content Area */}
      <div
        ref={selectionRef}
        className="flex-1 overflow-auto p-8"
        onMouseUp={handleTextSelection}
      >
        {/* Mock PDF Page */}
        <div className="bg-white shadow-lg rounded-lg p-12 max-w-4xl mx-auto min-h-[800px]">
          <div className="text-gray-700 leading-relaxed">
            <h2 className="text-2xl font-bold mb-4">Page {pageNumber}</h2>
            <p className="text-lg mb-4">
              Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
            </p>
            <p className="text-lg mb-4">
              Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
            </p>
            <p className="text-lg">
              Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
            </p>
          </div>
        </div>
      </div>

      {/* Bottom Controls */}
      <div className="bg-white border-t border-gray-200 p-4 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <button
            onClick={handlePreviousPage}
            disabled={pageNumber === 1}
            className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="px-4 py-1 bg-gray-100 rounded-md">
            {pageNumber} / {totalPages}
          </span>
          <button
            onClick={handleNextPage}
            disabled={pageNumber === totalPages}
            className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        {selectedText && (
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <span>Selected: {selectedText.substring(0, 50)}...</span>
            <button
              onClick={() => setSelectedText('')}
              className="text-red-500 hover:text-red-700"
            >
              Clear
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
