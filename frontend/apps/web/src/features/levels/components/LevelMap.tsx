import { Badge } from '@xian/ui';
import { DIFFICULTY_LABEL } from '@xian/types';
import type { Level, LevelProgress } from '@xian/types';
import { cn } from '../../../lib/utils/cn';

export interface LevelMapProps {
  levels: Level[];
  progress: LevelProgress[];
  onSelect: (level: Level) => void;
  selectedCode: string | null;
}

/** 关卡地图：路径式十关 + 锁定/通关动效（技术方案 8.4）。 */
export function LevelMap({ levels, progress, onSelect, selectedCode }: LevelMapProps) {
  const passed = new Set(progress.filter((p) => p.status === 'passed').map((p) => p.level_id));

  return (
    <ol className="space-y-2">
      {levels.map((lv, i) => {
        const done = passed.has(lv.id);
        const prevPassed = i === 0 || passed.has(levels[i - 1].id);
        const locked = !prevPassed && !done;
        return (
          <li key={lv.id}>
            <button
              type="button"
              disabled={locked}
              onClick={() => onSelect(lv)}
              className={cn(
                'flex w-full items-center gap-3 rounded-card border px-3 py-2.5 text-left transition-colors duration-fast',
                selectedCode === lv.id
                  ? 'border-blue-team bg-blue-team/10'
                  : done
                    ? 'border-success/40 bg-success/5'
                    : locked
                      ? 'border-border opacity-50'
                      : 'border-border hover:bg-white/5'
              )}
            >
              <span
                className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-mono text-xs font-bold',
                  done ? 'bg-success text-white' : locked ? 'bg-white/10 text-content-faint' : 'bg-blue-team text-white'
                )}
              >
                {done ? '✓' : i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-content">{lv.name}</p>
                <p className="truncate text-[11px] text-content-muted">{lv.goal}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Badge tone="coach">{DIFFICULTY_LABEL[lv.difficulty]}</Badge>
                {locked ? <Badge>未解锁</Badge> : null}
              </div>
            </button>
          </li>
        );
      })}
    </ol>
  );
}