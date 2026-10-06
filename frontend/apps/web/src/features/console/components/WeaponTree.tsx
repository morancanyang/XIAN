import { Tree, type TreeNode } from '@xian/ui';
import { Badge } from '@xian/ui';
import { DIFFICULTY_LABEL, SEVERITY_LABEL } from '@xian/types';
import type { AttackCase, AttackCategory } from '@xian/types';

export interface WeaponTreeProps {
  categories: AttackCategory[];
  cases: AttackCase[];
  onPick: (c: AttackCase) => void;
}

/** 武器库：14 类 → 用例树（技术方案 8.4 模式二三栏）。 */
export function WeaponTree({ categories, cases, onPick }: WeaponTreeProps) {
  const nodes: TreeNode[] = categories.map((cat) => ({
    id: cat.code,
    label: (
      <span className="flex items-center gap-2">
        <span className="font-mono text-[11px] text-blue-team">{cat.code}</span>
        <span className="truncate">{cat.name}</span>
        <Badge tone="neutral">{cases.filter((c) => c.category_id === cat.code).length}</Badge>
      </span>
    ),
    children: cases
      .filter((c) => c.category_id === cat.code)
      .map((c) => ({
        id: c.id,
        label: (
          <span className="flex items-center gap-2">
            <span className="truncate">{c.title}</span>
            <Badge tone={c.severity === 'critical' || c.severity === 'high' ? 'danger' : c.severity === 'medium' ? 'warning' : 'neutral'}>
              {SEVERITY_LABEL[c.severity]}
            </Badge>
            <span className="text-[10px] text-content-faint">{DIFFICULTY_LABEL[c.difficulty]}</span>
          </span>
        ),
        meta: `${Math.round(c.success_rate * 100)}%`
      }))
  }));

  const findCase = (id: string) => cases.find((c) => c.id === id);

  return (
    <Tree
      nodes={nodes}
      onSelect={(node) => {
        const hit = findCase(node.id);
        if (hit) onPick(hit);
      }}
    />
  );
}