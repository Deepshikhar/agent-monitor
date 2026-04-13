export type SessionStatus = "healthy" | "looping" | "drifting" | "failing";

export interface SessionSummary {
  session_id: string;
  status: SessionStatus;
  total_steps: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  action_distribution: Record<string, number>;
  issues: string[];
  last_updated: number;
}

export interface AgentEvent {
  session_id: string;
  timestamp: number;
  step: number | null;
  action: string;
  input: string;
  output: string;
  metadata: {
    status?: string;
    file?: string;
    [key: string]: unknown;
  };
}

export interface SessionDetail extends SessionSummary {
  events: AgentEvent[];
  insights: string[];
}
