import { CHAPTERS } from '@xian/types';
import { cn } from '../../../lib/utils/cn';

export interface ChapterNavProps {
  active: string;
  onSelect: (chapter: string) => void;
  className?: string;
}

/** 报告阅读左侧章节导航（技术方案 8.4）：九章，滚动高亮。 */
export function ChapterNav({ active, onSelect, className }: ChapterNavProps) {
  return (
    <nav className={cn('space-y-1', className)}>
      {CHAPTERS.map((chapter, i) => (
        <button
          key={chapter}
          type="button"
          onClick={() => onSelect(chapter)}
          className={cn(
            'flex w-full items-center gap-2 rounded-control px-3 py-2 text-left text-xs transition-colors duration-fast',
            active === chapter ? 'bg-blue-team/15 text-blue-team' : 'text-content-muted hover:bg-white/5 hover:text-content'
          )}
        >
          <span className="font-mono text-[10px] text-content-faint">{String(i + 1).padStart(2, '0')}</span>
          <span className="truncate">{chapter}</span>
        </button>
      ))}
    </nav>
  );
}