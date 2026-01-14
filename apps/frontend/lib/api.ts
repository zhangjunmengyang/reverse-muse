import type {
  LibraryResponse,
  LoadPaperResponse,
  StartSessionResponse,
  ActionResponse,
  PaperContentResponse,
  UserAction,
  UploadPaperResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001/api/v1';

/**
 * Sanitize text by removing lone surrogate characters that can't be encoded in UTF-8.
 * Valid surrogate pairs (like mathematical symbols 𝕏, 𝔸) are preserved.
 * Only unpaired/lone surrogates are removed.
 */
function sanitizeText(text: string): string {
  // Only remove lone surrogates (unpaired high/low surrogates)
  // Valid surrogate pairs: high surrogate (\uD800-\uDBFF) followed by low surrogate (\uDC00-\uDFFF)
  // This regex matches:
  // 1. High surrogate NOT followed by low surrogate
  // 2. Low surrogate NOT preceded by high surrogate
  return text
    .replace(/[\uD800-\uDBFF](?![\uDC00-\uDFFF])/g, '')  // lone high surrogate
    .replace(/(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/g, ''); // lone low surrogate
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || 'Request failed');
  }

  return response.json();
}

export const api = {
  // Library endpoints
  async getLibrary(): Promise<LibraryResponse> {
    return fetchApi<LibraryResponse>('/library/papers');
  },

  async loadPaper(paperId: string, userId: string = 'default_user'): Promise<LoadPaperResponse> {
    return fetchApi<LoadPaperResponse>('/library/load', {
      method: 'POST',
      body: JSON.stringify({ paper_id: paperId, user_id: userId }),
    });
  },

  async getPaperContent(paperId: string): Promise<PaperContentResponse> {
    return fetchApi<PaperContentResponse>(`/library/paper/${paperId}/content`);
  },

  getPdfUrl(paperId: string): string {
    return `${API_BASE}/library/paper/${paperId}/pdf`;
  },

  // Reading session endpoints
  async startSession(
    userId: string,
    paperId: string,
    sessionId: string
  ): Promise<StartSessionResponse> {
    return fetchApi<StartSessionResponse>('/reading/start', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        paper_id: paperId,
        session_id: sessionId,
      }),
    });
  },

  async recordAction(
    contextId: string,
    action: UserAction
  ): Promise<ActionResponse> {
    // Sanitize text fields to remove problematic Unicode characters
    const sanitizedAction = {
      ...action,
      selected_text: action.selected_text ? sanitizeText(action.selected_text) : undefined,
      context_text: action.context_text ? sanitizeText(action.context_text) : undefined,
      reading_position: {
        ...action.reading_position,
        text_snippet: action.reading_position.text_snippet
          ? sanitizeText(action.reading_position.text_snippet)
          : undefined,
      },
    };
    return fetchApi<ActionResponse>(`/reading/action?context_id=${contextId}`, {
      method: 'POST',
      body: JSON.stringify(sanitizedAction),
    });
  },

  // Upload paper
  async uploadPaper(file: File, userId: string = 'default_user'): Promise<UploadPaperResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${API_BASE}/pdf/upload?user_id=${encodeURIComponent(userId)}`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new ApiError(response.status, error.detail || 'Upload failed');
    }

    return response.json();
  },

  // Health check (endpoint is at root, not under /api/v1)
  async checkHealth(): Promise<{ status: string }> {
    const baseUrl = API_BASE.replace('/api/v1', '');
    const response = await fetch(`${baseUrl}/health`);
    if (!response.ok) {
      throw new ApiError(response.status, 'Health check failed');
    }
    return response.json();
  },
};

export { ApiError };
