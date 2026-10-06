import * as React from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MarkerType,
  type Node,
  type Edge,
  type NodeTypes,
  Position
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Badge } from '../primitives/Badge';
import { cn } from '../../lib/cn';

export interface AttackPathNodeData extends Record<string, unknown> {
  label: string;
  category: string;
  verdict?: 'success' | 'partial' | 'fail' | 'unavailable';
}

export interface AttackPathGraphProps {
  nodes: { id: string; label: string; category: string; verdict?: AttackPathNodeData['verdict'] }[];
  edges: { source: string; target: string }[];
  className?: string;
  height?: number;
  /** kill chain 阶段顺序：传入后按「一列一个阶段」排布，链路方向从左到右。 */
  stages?: string[];
}

const NODE_WIDTH = 190;
const COLUMN_GAP = 56;
const ROW_GAP = 18;

/** kill chain 攻击路径图（技术方案 8.4，基于 @xyflow/react）。 */
export function AttackPathGraph({ nodes, edges, className, height = 320, stages }: AttackPathGraphProps) {
  const layout = React.useMemo(() => {
    if (!stages || stages.length === 0) {
      return nodes.map((n, i) => ({
        id: n.id,
        position: { x: (i % 4) * 200, y: Math.floor(i / 4) * 120 }
      }));
    }
    // 按阶段分列：同一阶段纵向堆叠，列间距固定，读起来就是一条从左到右的攻击链
    const counters = new Map<string, number>();
    return nodes.map((n) => {
      const column = Math.max(0, stages.indexOf(n.category));
      const row = counters.get(n.category) ?? 0;
      counters.set(n.category, row + 1);
      return {
        id: n.id,
        position: { x: column * (NODE_WIDTH + COLUMN_GAP), y: row * (NODE_WIDTH + ROW_GAP) }
      };
    });
  }, [nodes, stages]);

  const flowNodes: Node<AttackPathNodeData>[] = React.useMemo(
    () =>
      nodes.map((n, i) => ({
        id: n.id,
        position: layout[i]?.position ?? { x: 0, y: 0 },
        data: { label: n.label, category: n.category, verdict: n.verdict },
        sourcePosition: Position.Right,
        targetPosition: Position.Left
      })),
    [nodes, layout]
  );

  const flowEdges: Edge[] = React.useMemo(
    () =>
      edges.map((e, i) => ({
        id: `e-${i}-${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-blue-team)' },
        style: { stroke: 'var(--color-blue-team)', strokeWidth: 1.5, opacity: 0.7 }
      })),
    [edges]
  );

  const nodeTypes: NodeTypes = React.useMemo(
    () => ({
      default: ({ data }: { data: AttackPathNodeData }) => (
        <div className="w-[190px] rounded-card border border-border bg-elevated px-3 py-2 shadow-card">
          <p className="truncate text-xs font-medium text-content" title={data.label}>
            {data.label}
          </p>
          <div className="mt-1 flex items-center gap-1">
            <span className="truncate font-mono text-[10px] text-content-faint">{data.category}</span>
            {data.verdict === 'success' ? <Badge tone="danger">命中</Badge> : null}
            {data.verdict === 'partial' ? <Badge tone="warning">部分</Badge> : null}
            {data.verdict === 'fail' ? <Badge tone="neutral">未命中</Badge> : null}
          </div>
        </div>
      )
    }),
    []
  );

  return (
    <div className={cn('rounded-card border border-border', className)} style={{ height }}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.16, maxZoom: 1 }}
          minZoom={0.3}
          proOptions={{ hideAttribution: true }}
          className="bg-sunken"
        >
          <Background color="var(--border)" gap={16} />
          <Controls showInteractive={false} className="!border-border !bg-elevated" />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}