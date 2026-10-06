import * as React from 'react';
import { Button } from './Button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from './Dialog';

export interface ConfirmDialogProps {
  open: boolean;
  title?: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void | Promise<void>;
  onOpenChange: (open: boolean) => void;
}

/** PRD 2.3.3：删除类操作一律二次确认。 */
export function ConfirmDialog({
  open,
  title = '确认操作',
  description = '该操作不可撤销，请再次确认。',
  confirmLabel = '确认',
  cancelLabel = '取消',
  destructive = false,
  onConfirm,
  onOpenChange
}: ConfirmDialogProps) {
  const [pending, setPending] = React.useState(false);

  React.useEffect(() => {
    if (!open) setPending(false);
  }, [open]);

  async function handleConfirm() {
    setPending(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } finally {
      setPending(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
            {cancelLabel}
          </Button>
          <Button variant={destructive ? 'danger' : 'primary'} loading={pending} onClick={handleConfirm}>
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}