import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';

const meta: Meta<typeof Button> = {
  title: 'Primitives/Button',
  component: Button,
  tags: ['autodocs'],
  argTypes: {
    variant: { control: 'select', options: ['primary', 'danger', 'outline', 'ghost', 'subtle'] },
    size: { control: 'select', options: ['sm', 'md', 'lg', 'icon'] }
  }
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = { args: { children: '发起战役' } };
export const Danger: Story = { args: { children: '删除实例', variant: 'danger' } };
export const Loading: Story = { args: { children: '执行中', loading: true } };
export const Outline: Story = { args: { children: '导出报告', variant: 'outline' } };