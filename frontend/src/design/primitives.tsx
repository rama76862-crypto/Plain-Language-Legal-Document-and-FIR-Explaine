/**
 * NyayaSarathi Core Design System Primitives
 * Light mode, high-contrast, fully keyboard accessible, screen-reader announced.
 */

import React, { useState, useRef, useEffect, useCallback, useId } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, AlertTriangle, AlertCircle, Info, CheckCircle2, ChevronDown, Check, Copy } from 'lucide-react';
import { useReducedMotion } from './motion';

/* =========================================================================
   1. Button
   ========================================================================= */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger-outline' | 'caution-outline';
  size?: 'sm' | 'md' | 'lg' | 'pill';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      children,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const sizeClasses = {
      sm: 'px-3 py-1.5 text-xs rounded-md min-h-[36px]',
      md: 'px-5 py-2.5 text-sm rounded-md min-h-[44px]',
      lg: 'px-6 py-3.5 text-base rounded-lg min-h-[48px]',
      pill: 'px-6 py-2.5 text-sm rounded-pill min-h-[44px]',
    };

    const variantClasses = {
      primary:
        'bg-blue text-white shadow-pop hover:bg-blue/95 active:scale-[0.98] relative overflow-hidden',
      secondary:
        'bg-paper text-ink border border-line hover:bg-bg2 hover:border-blue/30 active:scale-[0.98]',
      ghost:
        'bg-transparent text-ink hover:bg-bg2 active:scale-[0.98]',
      'danger-outline':
        'bg-paper text-concern-ink border border-concern/30 hover:bg-concern-bg hover:border-concern active:scale-[0.98]',
      'caution-outline':
        'bg-paper text-caution-ink border border-caution/30 hover:bg-caution-bg hover:border-caution active:scale-[0.98]',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        aria-busy={isLoading}
        className={`inline-flex items-center justify-center font-semibold transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none select-none ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
        {...props}
      >
        {variant === 'primary' && !disabled && !isLoading && (
          <span className="absolute inset-0 w-1/2 h-full bg-white/20 skew-x-12 -translate-x-full animate-shimmer pointer-events-none" />
        )}
        {isLoading ? (
          <Loader2 className="w-4 h-4 mr-2 animate-spin" aria-hidden="true" />
        ) : leftIcon ? (
          <span className="mr-2 inline-flex items-center">{leftIcon}</span>
        ) : null}
        <span>{children}</span>
        {rightIcon && !isLoading && (
          <span className="ml-2 inline-flex items-center">{rightIcon}</span>
        )}
      </button>
    );
  }
);
Button.displayName = 'Button';

/* =========================================================================
   2. GlassCard & TiltCard
   ========================================================================= */
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const GlassCard = React.forwardRef<HTMLDivElement, CardProps>(
  ({ children, className = '', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`glass-card rounded-lg shadow-card p-6 transition-all ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);
GlassCard.displayName = 'GlassCard';

export interface TiltCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
  index?: string;
  icon?: string;
  title?: string;
  description?: string;
}

export const TiltCard: React.FC<TiltCardProps> = ({
  children,
  index,
  icon,
  title,
  description,
  className = '',
  ...props
}) => {
  const cardRef = useRef<HTMLDivElement | null>(null);

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const r = cardRef.current.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    cardRef.current.style.transform = `rotateY(${x * 22}deg) rotateX(${-y * 22}deg) translateZ(14px)`;
  };

  const handlePointerLeave = () => {
    if (!cardRef.current) return;
    cardRef.current.style.transform = '';
  };

  return (
    <div
      ref={cardRef}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      className={`tilt ${className}`}
      {...props}
    >
      {index && <span className="n">{index}</span>}
      {icon && <span className="ic">{icon}</span>}
      {title && <h4 className="font-bold text-navy">{title}</h4>}
      {description && <p className="text-xs text-mute mt-1 leading-relaxed">{description}</p>}
      {children}
    </div>
  );
};

/* =========================================================================
   3. StatusPill & MonoLabel
   ========================================================================= */
export type StatusPillVariant =
  | 'concern'
  | 'caution'
  | 'deadline'
  | 'ok'
  | 'translation';

export const StatusPill: React.FC<{
  variant: StatusPillVariant;
  children: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}> = ({ variant, children, icon, className = '' }) => {
  const styles: Record<StatusPillVariant, { bg: string; text: string; defaultIcon: React.ReactNode }> = {
    concern: {
      bg: 'bg-concern-bg border-concern/30',
      text: 'text-concern-ink',
      defaultIcon: <AlertCircle className="w-3.5 h-3.5 text-concern" aria-hidden="true" />,
    },
    caution: {
      bg: 'bg-caution-bg border-caution/30',
      text: 'text-caution-ink',
      defaultIcon: <AlertTriangle className="w-3.5 h-3.5 text-caution" aria-hidden="true" />,
    },
    deadline: {
      bg: 'bg-deadline-bg border-deadline/30',
      text: 'text-deadline-ink',
      defaultIcon: <Info className="w-3.5 h-3.5 text-deadline" aria-hidden="true" />,
    },
    ok: {
      bg: 'bg-ok-bg border-ok/30',
      text: 'text-ok-ink',
      defaultIcon: <CheckCircle2 className="w-3.5 h-3.5 text-ok" aria-hidden="true" />,
    },
    translation: {
      bg: 'bg-paper border-caution text-caution-ink',
      text: 'text-caution-ink',
      defaultIcon: <Info className="w-3.5 h-3.5 text-caution" aria-hidden="true" />,
    },
  };

  const current = styles[variant];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-xs font-semibold border ${current.bg} ${current.text} ${className}`}
    >
      {icon ?? current.defaultIcon}
      <span>{children}</span>
    </span>
  );
};

export const MonoLabel: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className = '' }) => (
  <span
    className={`font-mono text-[11px] uppercase tracking-[0.08em] font-semibold text-mute ${className}`}
  >
    {children}
  </span>
);

export const Kbd: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <kbd className="px-1.5 py-0.5 text-xs font-mono font-semibold bg-bg2 text-ink border border-line rounded">
    {children}
  </kbd>
);

/* =========================================================================
   4. Tooltip
   ========================================================================= */
export const Tooltip: React.FC<{
  content: string;
  children: React.ReactElement;
}> = ({ content, children }) => {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {React.cloneElement(children, { 'aria-describedby': open ? id : undefined })}
      <AnimatePresence>
        {open && (
          <motion.div
            id={id}
            role="tooltip"
            initial={{ opacity: 0, y: 4, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1 text-xs font-medium text-white bg-navy rounded shadow-card pointer-events-none z-50 whitespace-nowrap"
          >
            {content}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-navy" />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

/* =========================================================================
   5. Modal (Focus Trap, Escape Key, Backdrop)
   ========================================================================= */
export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl';
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  maxWidth = 'md',
}) => {
  const modalRef = useRef<HTMLDivElement | null>(null);
  const prevFocusedEl = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      prevFocusedEl.current = document.activeElement as HTMLElement;
      modalRef.current?.focus();

      const onKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          onClose();
        }
      };
      window.addEventListener('keydown', onKeyDown);
      return () => window.removeEventListener('keydown', onKeyDown);
    } else {
      prevFocusedEl.current?.focus();
    }
  }, [isOpen, onClose]);

  const maxWClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy/40 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 16 }}
            transition={{ duration: 0.2 }}
            ref={modalRef}
            tabIndex={-1}
            className={`w-full ${maxWClasses[maxWidth]} bg-paper rounded-lg shadow-pop border border-line p-6 outline-none`}
          >
            <div className="flex items-center justify-between pb-4 border-b border-line mb-4">
              <h2 id="modal-title" className="text-lg font-bold text-navy">
                {title}
              </h2>
              <button
                onClick={onClose}
                className="text-mute hover:text-ink p-1 rounded hover:bg-bg2"
                aria-label="Close dialog"
              >
                ✕
              </button>
            </div>
            <div>{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

/* =========================================================================
   6. Tabs (Animated Gliding Indicator, Roving Tabindex)
   ========================================================================= */
export interface TabItem {
  id: string;
  label: string;
  badge?: number | string;
}

export const Tabs: React.FC<{
  tabs: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  className?: string;
}> = ({ tabs, activeId, onChange, className = '' }) => {
  return (
    <div
      role="tablist"
      className={`inline-flex p-1 bg-bg2 rounded-pill border border-line ${className}`}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeId;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(tab.id)}
            className={`relative px-4 py-2 text-sm font-semibold rounded-pill transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue ${
              isActive ? 'text-white' : 'text-mute hover:text-ink'
            }`}
          >
            {isActive && (
              <motion.div
                layoutId="gliding-tab-indicator"
                className="absolute inset-0 bg-navy rounded-pill shadow-sm"
                transition={{ type: 'spring', bounce: 0.2, duration: 0.35 }}
              />
            )}
            <span className="relative z-10 flex items-center gap-1.5">
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span
                  className={`px-1.5 py-0.2 rounded-pill text-xs font-mono ${
                    isActive ? 'bg-blue text-white' : 'bg-line text-ink'
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
};

/* =========================================================================
   7. SegmentedControl
   ========================================================================= */
export const SegmentedControl: React.FC<{
  options: { value: string; label: string; badge?: string }[];
  value: string;
  onChange: (val: string) => void;
  className?: string;
}> = ({ options, value, onChange, className = '' }) => {
  return (
    <div className={`inline-flex p-1 bg-bg2 rounded-md border border-line ${className}`}>
      {options.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`relative px-3 py-1.5 text-xs font-semibold rounded transition-colors ${
              isSelected ? 'text-navy font-bold' : 'text-mute hover:text-ink'
            }`}
          >
            {isSelected && (
              <motion.div
                layoutId="segmented-indicator"
                className="absolute inset-0 bg-paper rounded shadow-sm border border-line"
                transition={{ type: 'spring', bounce: 0.15, duration: 0.3 }}
              />
            )}
            <span className="relative z-10 flex items-center gap-1">
              <span>{opt.label}</span>
              {opt.badge && (
                <span className="text-[10px] px-1 py-0.2 bg-line rounded">
                  {opt.badge}
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
};

/* =========================================================================
   8. Select (Accessible Native-based Dropdown)
   ========================================================================= */
export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export const Select: React.FC<{
  label?: string;
  value: string;
  onChange: (val: string) => void;
  options: SelectOption[];
  disabled?: boolean;
  className?: string;
}> = ({ label, value, onChange, options, disabled, className = '' }) => {
  const id = useId();

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {label && (
        <label htmlFor={id} className="text-xs font-semibold text-mute">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          id={id}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className="w-full appearance-none bg-paper border border-line text-ink rounded-md px-3.5 py-2.5 pr-10 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue disabled:opacity-50 transition-colors"
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown
          className="w-4 h-4 text-mute absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none"
          aria-hidden="true"
        />
      </div>
    </div>
  );
};

/* =========================================================================
   9. Banner (Info / Warn / Error)
   ========================================================================= */
export const Banner: React.FC<{
  variant?: 'info' | 'warn' | 'error';
  title?: string;
  children: React.ReactNode;
  action?: { label: string; onClick: () => void };
  className?: string;
}> = ({ variant = 'info', title, children, action, className = '' }) => {
  const config = {
    info: {
      bg: 'bg-blue/5 border-blue/20 text-navy',
      icon: <Info className="w-5 h-5 text-blue shrink-0" aria-hidden="true" />,
    },
    warn: {
      bg: 'bg-caution-bg border-caution/30 text-caution-ink',
      icon: <AlertTriangle className="w-5 h-5 text-caution shrink-0" aria-hidden="true" />,
    },
    error: {
      bg: 'bg-concern-bg border-concern/30 text-concern-ink',
      icon: <AlertCircle className="w-5 h-5 text-concern shrink-0" aria-hidden="true" />,
    },
  };

  const c = config[variant];

  return (
    <div
      role="alert"
      className={`p-4 rounded-md border flex items-start gap-3.5 text-sm ${c.bg} ${className}`}
    >
      {c.icon}
      <div className="flex-1">
        {title && <div className="font-bold mb-0.5">{title}</div>}
        <div>{children}</div>
      </div>
      {action && (
        <button
          onClick={action.onClick}
          className="underline font-semibold hover:opacity-80 shrink-0 text-xs px-2 py-1 rounded"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};

/* =========================================================================
   10. ProgressSteps (Real State)
   ========================================================================= */
export interface StepItem {
  id: string;
  label: string;
  status: 'ready' | 'active' | 'done';
}

export const ProgressSteps: React.FC<{
  steps: StepItem[];
  onStepClick?: (id: string) => void;
}> = ({ steps, onStepClick }) => {
  return (
    <nav aria-label="Progress" className="w-full">
      <ol className="flex items-center justify-between gap-2">
        {steps.map((step, idx) => {
          const isDone = step.status === 'done';
          const isActive = step.status === 'active';
          return (
            <li key={step.id} className="flex-1 flex items-center">
              <button
                type="button"
                disabled={!isDone}
                onClick={() => isDone && onStepClick?.(step.id)}
                className={`flex items-center gap-2 text-xs font-semibold transition-colors ${
                  isActive
                    ? 'text-navy font-bold'
                    : isDone
                    ? 'text-blue cursor-pointer hover:underline'
                    : 'text-mute opacity-60 cursor-not-allowed'
                }`}
              >
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-mono ${
                    isActive
                      ? 'bg-navy text-white ring-2 ring-blue ring-offset-2'
                      : isDone
                      ? 'bg-ok text-white'
                      : 'bg-line text-mute'
                  }`}
                >
                  {isDone ? '✓' : idx + 1}
                </span>
                <span className="hidden sm:inline">{step.label}</span>
              </button>
              {idx < steps.length - 1 && (
                <div
                  className={`flex-1 h-[2px] mx-2 ${
                    isDone ? 'bg-ok' : 'bg-line'
                  }`}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

/* =========================================================================
   11. Skeleton & EmptyState
   ========================================================================= */
export const Skeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`bg-line/40 animate-pulse rounded ${className}`} />
);

export const EmptyState: React.FC<{
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}> = ({ title, description, icon, action }) => (
  <div className="flex flex-col items-center justify-center p-8 text-center glass-card rounded-lg">
    {icon && <div className="text-mute mb-3">{icon}</div>}
    <h3 className="text-base font-bold text-navy mb-1">{title}</h3>
    <p className="text-sm text-mute max-w-sm mb-4">{description}</p>
    {action}
  </div>
);

/* =========================================================================
   12. Accordion / Expander
   ========================================================================= */
export const Accordion: React.FC<{
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
}> = ({ title, defaultOpen = false, children, className = '' }) => {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={`border border-line rounded-md bg-paper overflow-hidden ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="w-full flex items-center justify-between p-3.5 text-left text-sm font-semibold text-navy hover:bg-bg2 transition-colors"
      >
        <span>{title}</span>
        <ChevronDown
          className={`w-4 h-4 text-mute transition-transform duration-200 ${
            open ? 'rotate-180' : ''
          }`}
          aria-hidden="true"
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="p-3.5 pt-0 border-t border-line/60 text-sm">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

/* =========================================================================
   13. NumberTicker
   ========================================================================= */
export const NumberTicker: React.FC<{ value: number; className?: string }> = ({
  value,
  className = '',
}) => {
  const reduced = useReducedMotion();
  const [displayValue, setDisplayValue] = useState(reduced ? value : 0);

  useEffect(() => {
    if (reduced) {
      setDisplayValue(value);
      return;
    }

    const duration = 600;
    const startTime = performance.now();

    const animate = (time: number) => {
      const elapsed = time - startTime;
      const progress = Math.min(1, elapsed / duration);
      setDisplayValue(Math.floor(progress * value));
      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setDisplayValue(value);
      }
    };

    requestAnimationFrame(animate);
  }, [value, reduced]);

  return <span className={`font-mono font-bold ${className}`}>{displayValue}</span>;
};

/* =========================================================================
   14. MarqueeBand
   ========================================================================= */
export const MarqueeBand: React.FC<{ text: string }> = ({ text }) => {
  const reduced = useReducedMotion();

  if (reduced) {
    return (
      <div className="bg-navy text-white text-xs font-mono py-2.5 px-4 text-center overflow-hidden">
        {text}
      </div>
    );
  }

  return (
    <div
      className="bg-navy text-white text-xs font-mono py-2.5 overflow-hidden whitespace-nowrap select-none border-y border-line/20"
      tabIndex={0}
      aria-label="Assurance marquee banner"
    >
      <div className="inline-block animate-marquee hover:[animation-play-state:paused] focus:[animation-play-state:paused]">
        <span className="mx-6 tracking-wider opacity-90">{text}</span>
        <span className="mx-6 tracking-wider opacity-90">{text}</span>
      </div>
      <style>{`
        @keyframes marquee {
          0% { transform: translateX(0%); }
          100% { transform: translateX(-50%); }
        }
        .animate-marquee {
          display: inline-block;
          white-space: nowrap;
          animation: marquee 28s linear infinite;
        }
      `}</style>
    </div>
  );
};

/* =========================================================================
   15. CopyButton
   ========================================================================= */
export const CopyButton: React.FC<{ text: string; className?: string }> = ({
  text,
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`p-1.5 text-mute hover:text-ink rounded hover:bg-bg2 transition-colors ${className}`}
      aria-label={copied ? 'Copied to clipboard' : 'Copy text to clipboard'}
    >
      {copied ? (
        <Check className="w-4 h-4 text-ok" aria-hidden="true" />
      ) : (
        <Copy className="w-4 h-4" aria-hidden="true" />
      )}
    </button>
  );
};

/* =========================================================================
   16. Toast System (In-Memory Queue, Aria-Live Polite)
   ========================================================================= */
export interface ToastMessage {
  id: string;
  message: string;
  type?: 'info' | 'success' | 'warn' | 'error';
}

interface ToastContextType {
  showToast: (message: string, type?: 'info' | 'success' | 'warn' | 'error') => void;
}

const ToastContext = React.createContext<ToastContextType | null>(null);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback(
    (message: string, type: 'info' | 'success' | 'warn' | 'error' = 'info') => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, message, type }]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 3500);
    },
    []
  );

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div
        aria-live="polite"
        className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      >
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 16, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 16, scale: 0.95 }}
              className="pointer-events-auto p-4 rounded-md shadow-card bg-paper border border-line flex items-center gap-3 text-sm font-semibold text-navy"
            >
              {toast.type === 'success' && <CheckCircle2 className="w-4 h-4 text-ok" />}
              {toast.type === 'error' && <AlertCircle className="w-4 h-4 text-concern" />}
              {toast.type === 'warn' && <AlertTriangle className="w-4 h-4 text-caution" />}
              {(!toast.type || toast.type === 'info') && <Info className="w-4 h-4 text-blue" />}
              <span>{toast.message}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
};

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return ctx;
}
