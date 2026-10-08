// MenQ brand expression (D-027) — core component types. Runtime: window.MenQ (React 18 UMD + components/bundle.js).
import type React from 'react';
type Node = React.ReactNode;
export type Tone = 'neutral' | 'accent' | 'glass' | 'info' | 'success' | 'warning' | 'danger';
export type Status = 'online' | 'busy' | 'offline' | 'error';
export type ThemePreference = 'system' | 'light' | 'dark';
export interface BrandMarkProps { compact?: boolean; admin?: boolean; tag?: string; /** play the power-on animation once (hero, splash, loading only) */ powerOn?: boolean; className?: string; }
export interface ButtonProps { children?: Node; variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'; size?: 'sm' | 'md' | 'lg'; small?: boolean; loading?: boolean; disabled?: boolean; icon?: Node; href?: string; type?: 'button' | 'submit' | 'reset'; title?: string; className?: string; onClick?: (e: React.MouseEvent) => void; }
export interface CardProps { children?: Node; variant?: 'solid' | 'elevated' | 'outline' | 'glass' | 'brand' | 'premium'; interactive?: boolean; className?: string; style?: React.CSSProperties; }
export interface PanelProps { title?: Node; actions?: Node; children?: Node; }
export interface PageHeaderProps { title: Node; subtitle?: Node; actions?: Node; }
export interface SectionHeadingProps { title: Node; index?: string; eyebrow?: Node; description?: Node; align?: 'center' | 'left'; as?: 'h1' | 'h2'; children?: Node; }
export interface BadgeProps { children?: Node; tone?: Tone; variant?: Tone; dot?: boolean; }
export interface StatusDotProps { status: Status; label?: string; }
export interface AvatarProps { name: string; src?: string; kind?: string; }
export interface FieldProps { label: Node; children?: Node; }
export type InputProps = React.InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean };
export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean };
export type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean };
export interface FormRowProps { label: Node; hint?: Node; error?: Node; required?: boolean; id?: string; /** exactly one control; it receives id, aria-describedby and aria-invalid */ children: React.ReactElement; }
export type CheckboxProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> & { label: Node; hint?: Node; invalid?: boolean };
export interface RadioOption { value: string; label: Node; hint?: Node; disabled?: boolean; }
export interface RadioGroupProps { label: Node; options: RadioOption[]; name?: string; value?: string; defaultValue?: string; onChange?: (value: string) => void; error?: Node; disabled?: boolean; }
export interface IconProps { /** 24-grid stroke paths (e.g. Lucide) */ children?: Node; size?: 'sm' | 'md' | 'lg'; /** set when the icon carries meaning; otherwise it is aria-hidden */ label?: string; strokeWidth?: number; className?: string; }
export interface AccordionItem { id: string; title: Node; content: Node; }
export interface AccordionProps { items: AccordionItem[]; multiple?: boolean; open?: string[]; defaultOpen?: string[]; onChange?: (open: string[]) => void; headingLevel?: 2 | 3 | 4 | 5 | 6; id?: string; }
export interface NavItem { href: string; label: Node; current?: boolean; icon?: Node; onClick?: (e: React.MouseEvent) => void; }
export interface NavProps { label: string; items: NavItem[]; orientation?: 'horizontal' | 'vertical'; className?: string; }
export interface TooltipProps { content: Node; /** exactly one focusable trigger */ children: React.ReactElement; placement?: 'top' | 'bottom'; delay?: number; id?: string; }
export interface RevealProps { children?: Node; pattern?: 'fade' | 'rise' | 'rise-sm' | 'scale'; /** stagger position among siblings, capped at 8 */ index?: number; as?: string; id?: string; className?: string; style?: React.CSSProperties; }
export interface SwitchProps { label: Node; hint?: Node; checked?: boolean; defaultChecked?: boolean; onChange?: (checked: boolean) => void; disabled?: boolean; }
export interface TabsProps { items: { value: string; label: Node; count?: number; id?: string; controls?: string }[]; label?: string; defaultValue?: string; value?: string; onChange?: (value: string) => void; }
export interface LocaleSwitchProps { value?: 'hy' | 'en' | 'ru'; defaultValue?: 'hy' | 'en' | 'ru'; label?: string; onChange?: (locale: 'hy' | 'en' | 'ru') => void; }
export interface ThemeSwitchProps { value?: ThemePreference; defaultValue?: ThemePreference; label?: string; labels?: { system?: string; light?: string; dark?: string }; apply?: boolean; onChange?: (pref: ThemePreference) => void; }
export interface EmptyStateProps { title: Node; hint?: Node; glyph?: Node; action?: Node; }
export interface SkeletonProps { rows?: number; }
export interface ToastProps { children?: Node; tone?: 'success' | 'info' | 'error'; onDismiss?: () => void; dismissLabel?: string; }
export interface ModalProps { title: string; onClose?: () => void; inline?: boolean; children?: Node; }
export interface ConfirmDialogProps { title: string; message: Node; confirmLabel: Node; cancelLabel: Node; onConfirm?: () => void; onCancel?: () => void; inline?: boolean; }
export interface DrawerProps { title: string; onClose?: () => void; inline?: boolean; closeLabel?: string; children?: Node; }
export interface KpiStatProps { label: Node; value: number; unit?: string; delta?: number; deltaLabel?: Node; locale?: string; variant?: CardProps['variant']; }
export interface MetricBarProps { label: string; value: number; display?: Node; }
export interface TableColumn<R> { key: string; label: Node; align?: 'left' | 'right' | 'center'; render?: (row: R) => Node; }
export interface TableProps<R = Record<string, unknown>> { columns: TableColumn<R>[]; rows: R[]; caption?: Node; }
export interface ContrastSectionProps { children?: Node; spotlight?: boolean; grid?: boolean; labelledBy?: string; className?: string; }
type C<P> = (props: P) => React.ReactElement | null;
export interface MenQCore {
  BrandMark: C<BrandMarkProps>; Button: C<ButtonProps>; Card: C<CardProps>; Panel: C<PanelProps>; PageHeader: C<PageHeaderProps>; SectionHeading: C<SectionHeadingProps>;
  Badge: C<BadgeProps>; StatusDot: C<StatusDotProps>; Avatar: C<AvatarProps>; Field: C<FieldProps>; Input: C<InputProps>; Textarea: C<TextareaProps>; Select: C<SelectProps>; FormRow: C<FormRowProps>; Checkbox: C<CheckboxProps>; RadioGroup: C<RadioGroupProps>; Switch: C<SwitchProps>; Icon: C<IconProps>; Accordion: C<AccordionProps>; Nav: C<NavProps>; Tooltip: C<TooltipProps>; Reveal: C<RevealProps>;
  Tabs: C<TabsProps>; LocaleSwitch: C<LocaleSwitchProps>; ThemeSwitch: C<ThemeSwitchProps>; EmptyState: C<EmptyStateProps>; Skeleton: C<SkeletonProps>; Toast: C<ToastProps>;
  Modal: C<ModalProps>; ConfirmDialog: C<ConfirmDialogProps>; Drawer: C<DrawerProps>; KpiStat: C<KpiStatProps>; MetricBar: C<MetricBarProps>; Table: C<TableProps>; ContrastSection: C<ContrastSectionProps>;
  applyTheme(pref: ThemePreference): void;
}
declare global { interface Window { MenQ: MenQCore; } }
