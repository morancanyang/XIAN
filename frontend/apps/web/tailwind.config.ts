import type { Config } from 'tailwindcss';
import preset from '@xian/config/tailwind-preset';

const config: Config = {
  presets: [preset],
  content: ['./index.html', './src/**/*.{ts,tsx}', '../../packages/ui/src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      backgroundImage: {
        'grid-faint':
          'linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)'
      }
    }
  },
  plugins: []
};

export default config;