// API Types
export interface Paper {
  paper_id: string;
  filename: string;
  title: string;
  author: string;
  page_count: number;
  file_path?: string;
}

export interface PageContent {
  page_number: number;
  content: string;
}

export interface ReadingPosition {
  paper_id: string;
  page_number: number;
  bbox?: { x1: number; y1: number; x2: number; y2: number };
  text_snippet?: string;
}

export interface Insight {
  id: string;
  content: string;
  insight_type: 'connection' | 'explanation' | 'question' | 'suggestion';
  confidence: number;
  status?: 'generating' | 'complete';
  timestamp?: string;
}

export interface ReadingSession {
  context_id: string;
  paper_id: string;
  user_id: string;
  started_at?: string;
}

export interface UserAction {
  trigger_type: 'selection' | 'linger' | 'scroll' | 'backtrack';
  reading_position: ReadingPosition;
  selected_text?: string;
  context_text?: string;
}

// UI State Types
export interface BubblePosition {
  x: number;
  y: number;
}

export interface ActiveBubble {
  insight: Insight;
  position: BubblePosition;
}

// API Response Types
export interface LibraryResponse {
  papers: Paper[];
  total: number;
}

export interface LoadPaperResponse {
  paper_id: string;
  title: string;
  page_count: number;
  chunk_count: number;
  message: string;
}

export interface StartSessionResponse {
  context_id: string;
  paper_id: string;
}

export interface ActionResponse {
  action_recorded: boolean;
  insight?: Insight;
}

export interface PaperContentResponse {
  paper_id: string;
  title: string;
  pages: PageContent[];
}

export interface UploadPaperResponse {
  paper_id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
  message: string;
}
