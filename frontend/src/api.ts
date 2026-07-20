import type {
  ArchiveExplorerResponse,
  EchoesResponse,
  JobStatusResponse,
  PostCreateResponse,
  PostSummary,
  SimilarPostsResponse
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api").replace(/\/$/, "");

async function readErrorMessage(response: Response, fallback: string) {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
    if (Array.isArray(payload?.detail) && payload.detail.length > 0) {
      const first = payload.detail[0];
      const field = Array.isArray(first?.loc) ? first.loc.at(-1) : null;
      const message = typeof first?.msg === "string" ? first.msg : null;
      if (field && message) {
        return `${String(field)}: ${message}`;
      }
      if (message) {
        return message;
      }
    }
  } catch {
    return fallback;
  }
  return fallback;
}

export async function fetchPosts(): Promise<PostSummary[]> {
  const response = await fetch(`${API_BASE}/posts`);
  if (!response.ok) {
    throw new Error("Failed to load posts.");
  }
  return response.json();
}

export async function createPost(payload: {
  text: string;
  about?: string;
  mood?: string;
  content_notes?: string[];
}): Promise<PostCreateResponse> {
  const response = await fetch(`${API_BASE}/posts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "Failed to create post."));
  }
  return response.json();
}

export async function fetchJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error("Failed to load job status.");
  }
  return response.json();
}

export async function fetchPost(postId: number): Promise<PostSummary> {
  const response = await fetch(`${API_BASE}/posts/${postId}`);
  if (!response.ok) {
    throw new Error("Failed to load the story.");
  }
  return response.json();
}

export async function fetchSimilarPosts(postId: number, limit = 5): Promise<SimilarPostsResponse> {
  const response = await fetch(`${API_BASE}/posts/${postId}/similar?limit=${limit}`);
  if (!response.ok) {
    throw new Error("Failed to find similar posts.");
  }
  return response.json();
}

export async function fetchEchoes(postId: number, depth = 5): Promise<EchoesResponse> {
  const response = await fetch(`${API_BASE}/posts/${postId}/echoes?depth=${depth}`);
  if (!response.ok) {
    throw new Error("Failed to trace connected writings.");
  }
  return response.json();
}

export async function fetchArchiveExplorer(params?: {
  theme?: string;
  emotion?: string;
  tone?: string;
  author?: string;
  year?: string;
  content_type?: string;
  collection?: string;
  content_note?: string;
  avoid_theme?: string;
  avoid_content_note?: string;
  sort?: string;
  semantic_to_post_id?: number;
}): Promise<ArchiveExplorerResponse> {
  const search = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        search.set(key, String(value));
      }
    });
  }
  const suffix = search.toString() ? `?${search.toString()}` : "";
  const response = await fetch(`${API_BASE}/archive/explorer${suffix}`);
  if (!response.ok) {
    throw new Error("Failed to load the archive explorer.");
  }
  return response.json();
}
