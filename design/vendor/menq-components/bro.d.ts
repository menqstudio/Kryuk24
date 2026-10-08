// MenQ product extension: Bro (D-027). Runtime: window.MenQ.Bro (requires the brand-expression core bundle).
import type React from 'react';
import type { Status } from '../../../brand-expression/components/index';
type Node = React.ReactNode;
export interface TimelineProps { items: { title: Node; meta?: Node; detail?: Node; state?: 'done' | 'running' | 'waiting' | 'failed' | 'pending' }[]; }
export interface ChatMessageProps { role?: 'human' | 'bro' | 'agent'; author: string; children?: Node; time?: string; scope?: string; state?: 'running' | 'done' | 'failed'; stateLabel?: string; mine?: boolean; avatarSrc?: string; }
export interface AgentCardProps { name: string; role?: Node; status: Status; statusLabel?: string; scope?: string[]; task?: Node; taskLabel?: Node; progress?: number; progressLabel?: string; }
export interface ApprovalCardProps { title: Node; risk?: 'low' | 'medium' | 'high'; riskLabel?: Node; kicker?: Node; description?: Node; requestedBy?: string; approveLabel?: Node; rejectLabel?: Node; onApprove?: () => void; onReject?: () => void; }
export interface CommandComposerProps { onSubmit?: (text: string) => void; placeholder?: string; hint?: string; sendLabel?: Node; label?: string; }
type C<P> = (props: P) => React.ReactElement | null;
export interface MenQBro { avatarSrc: string | null; Timeline: C<TimelineProps>; ChatMessage: C<ChatMessageProps>; AgentCard: C<AgentCardProps>; ApprovalCard: C<ApprovalCardProps>; CommandComposer: C<CommandComposerProps>; }
declare global { interface Window { MenQ: import('../../../brand-expression/components/index').MenQCore & { Bro: MenQBro }; } }
