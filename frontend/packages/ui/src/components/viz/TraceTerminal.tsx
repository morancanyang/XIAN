import * as React from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { cn } from '../../lib/cn';

export interface TraceTerminalProps {
  lines: string[];
  className?: string;
  height?: number;
}

/** trace 回放终端（xterm 风格，技术方案 8.4 / 8.5）。 */
export function TraceTerminal({ lines, className, height = 220 }: TraceTerminalProps) {
  const hostRef = React.useRef<HTMLDivElement | null>(null);
  const termRef = React.useRef<Terminal | null>(null);
  const fitRef = React.useRef<FitAddon | null>(null);

  React.useEffect(() => {
    if (!hostRef.current) return;
    const term = new Terminal({
      fontFamily: 'var(--font-mono)',
      fontSize: 12,
      theme: {
        background: '#0b0f17',
        foreground: '#e5e7eb',
        cursor: '#3b82f6',
        selectionBackground: 'rgba(59,130,246,0.35)'
      },
      convertEol: true,
      scrollback: 5000
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(hostRef.current);
    fit.fit();
    termRef.current = term;
    fitRef.current = fit;

    const observer = new ResizeObserver(() => fitRef.current?.fit());
    observer.observe(hostRef.current);
    return () => {
      observer.disconnect();
      term.dispose();
      termRef.current = null;
    };
  }, []);

  React.useEffect(() => {
    const term = termRef.current;
    if (!term) return;
    term.clear();
    for (const line of lines.slice(-500)) term.writeln(line);
  }, [lines]);

  return (
    <div
      ref={hostRef}
      className={cn('overflow-hidden rounded-control border border-border bg-base', className)}
      style={{ height }}
    />
  );
}