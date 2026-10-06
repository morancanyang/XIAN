import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Dialog, DialogContent, DialogHeader, DialogTitle, Input, Kbd } from '@xian/ui';
import { ROUTES } from '@xian/types';

interface Command {
  id: string;
  title: string;
  path: string;
}

const COMMANDS: Command[] = [
  { id: 'home', title: '驾驶舱', path: '/dashboard' },
  { id: 'agents', title: 'Agent 资产', path: '/agents' },
  { id: 'scenarios', title: '靶场场景', path: '/scenarios' },
  { id: 'campaigns', title: '模式一 · 战役', path: '/campaigns' },
  { id: 'console', title: '模式二 · 自由攻击', path: '/console' },
  { id: 'levels', title: '十关挑战', path: '/levels' },
  { id: 'matrix', title: '攻击矩阵', path: '/matrix' },
  { id: 'reports', title: '报告中心', path: '/reports' },
  { id: 'admin', title: '管理后台', path: '/admin' },
  { id: 'profile', title: '个人中心', path: '/profile' }
];

/** 命令面板 Ctrl+K（技术方案 8.3）。 */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const results = COMMANDS.filter((c) => c.title.includes(query) || c.id.includes(query.toLowerCase()));

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="w-[min(520px,calc(100vw-2rem))]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            命令面板 <Kbd>Ctrl</Kbd>
            <Kbd>K</Kbd>
          </DialogTitle>
        </DialogHeader>
        <Input
          autoFocus
          placeholder="跳转到页面…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setCursor(0);
          }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              setCursor((c) => Math.min(c + 1, results.length - 1));
            }
            if (e.key === 'ArrowUp') {
              e.preventDefault();
              setCursor((c) => Math.max(c - 1, 0));
            }
            if (e.key === 'Enter' && results[cursor]) {
              navigate(results[cursor].path);
              setOpen(false);
              setQuery('');
            }
          }}
        />
        <ul className="mt-3 max-h-72 space-y-1 overflow-y-auto">
          {results.map((c, i) => (
            <li key={c.id}>
              <button
                type="button"
                className={`w-full rounded-control px-3 py-2 text-left text-sm ${
                  i === cursor ? 'bg-blue-team/15 text-blue-team' : 'text-content-muted hover:bg-white/5'
                }`}
                onClick={() => {
                  navigate(c.path);
                  setOpen(false);
                }}
              >
                {c.title}
              </button>
            </li>
          ))}
          {results.length === 0 ? <li className="px-3 py-6 text-center text-xs text-content-faint">无匹配</li> : null}
        </ul>
      </DialogContent>
    </Dialog>
  );
}

export { ROUTES };

