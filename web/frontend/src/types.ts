export type DiscussionMode = 'single' | 'summary' | 'meeting'

export interface FundRef { code: string; name: string }
export interface Manager {
  id: string
  name: string
  institution: string
  role: string
  color: string
  avatar: string
  tags: string[]
  representative_funds: FundRef[]
  corpus_files: number
  fund_files: number
  profile_excerpt: string
  method_excerpt: string
}
export interface Settings {
  deepseek_configured: boolean
  deepseek_key_masked: string | null
  model: string
  output_language: string
  summary_format: string
  api_available: boolean | null
  balance_infos: Array<{ currency: string; total_balance: string; granted_balance: string; topped_up_balance: string }>
  models: string[]
  last_checked_at: string | null
}
export interface IndexStatus {
  state: 'empty' | 'building' | 'ready' | 'degraded' | 'failed'
  files: number
  chunks: number
  embedding_model: string
  vector_enabled: boolean
  last_built_at: string | null
  error: string | null
}
export interface Evidence {
  quote: string
  source_file: string
  title: string
  date?: string
  chunk_id?: string
  excerpt: string
}
export interface ManagerView {
  manager_id: string
  manager_name: string
  position: string
  direct_evidence: Evidence[]
  method_inference: string[]
  holdings_evidence: Evidence[]
  missing_information: string[]
  confidence: 'high' | 'medium' | 'low'
  stage: 'analysis' | 'opening' | 'response'
}
export interface Message {
  id: string
  role: 'user' | 'manager' | 'assistant'
  manager_id?: string
  round_no?: number
  content: string
  citations: Evidence[]
  created_at: string
  run_id: string
}
export interface Run {
  id: string
  thread_id: string
  question: string
  status: string
  final_report: string
  error?: string
  created_at: string
  completed_at?: string
}
export interface Thread {
  id: string
  title: string
  mode: DiscussionMode
  manager_ids: string[]
  status: string
  last_summary: string
  created_at: string
  updated_at: string
  runs: Run[]
  messages: Message[]
}
