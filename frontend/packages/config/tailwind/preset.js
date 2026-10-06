/**
 * XIAN Design Tokens（技术方案 8.2）的 Tailwind preset。
 * 业务代码只允许引用 token，不允许硬编码色值（PRD 8.7.2 全局约束）。
 */
export default {
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        red: { team: 'var(--color-red-team)' },
        blue: { team: 'var(--color-blue-team)' },
        coach: 'var(--color-coach)',
        /* 顶层别名：组件库统一使用 bg-elevated / bg-sunken 这类简写，
           缺少这两项会导致所有「抬升表面」（Card / Dialog / Toast / 下拉菜单）
           背景解析为透明。保留 base.* 以兼容既有写法。 */
        elevated: 'var(--bg-elevated)',
        sunken: 'var(--bg-sunken)',
        base: {
          DEFAULT: 'var(--bg-base)',
          elevated: 'var(--bg-elevated)',
          sunken: 'var(--bg-sunken)'
        },
        border: {
          DEFAULT: 'var(--border)',
          strong: 'var(--border-strong)'
        },
        content: {
          DEFAULT: 'var(--text-primary)',
          muted: 'var(--text-secondary)',
          faint: 'var(--text-tertiary)'
        },
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
        danger: 'var(--color-danger)'
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
        cjk: ['var(--font-cjk)']
      },
      borderRadius: {
        control: 'var(--radius-control)',
        card: 'var(--radius-card)',
        pill: 'var(--radius-pill)'
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        float: 'var(--shadow-float)'
      },
      transitionDuration: {
        fast: 'var(--dur-fast)',
        base: 'var(--dur-base)',
        slow: 'var(--dur-slow)'
      },
      transitionTimingFunction: {
        out: 'var(--ease-out)'
      },
      zIndex: {
        sticky: 'var(--z-sticky)',
        dropdown: 'var(--z-dropdown)',
        modal: 'var(--z-modal)',
        toast: 'var(--z-toast)',
        alert: 'var(--z-alert)'
      },
      keyframes: {
        'slide-in': {
          from: { opacity: '0', transform: 'translateY(-6px)' },
          to: { opacity: '1', transform: 'translateY(0)' }
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.35' }
        }
      },
      animation: {
        'slide-in': 'slide-in var(--dur-base) var(--ease-out)',
        pulse: 'pulse 1s ease-in-out infinite'
      }
    }
  }
};
