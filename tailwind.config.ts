import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#0A0A0F',
          panel: '#0F0F17',
          card: '#16161F',
          hover: '#1C1C28',
          border: '#1E1E2E',
        },
        accent: {
          DEFAULT: '#22D3EE',
          dim: '#0E7490',
          glow: '#22D3EE33',
        },
        fuel: {
          cheap: '#4ADE80',
          mid: '#FACC15',
          expensive: '#F87171',
        },
        text: {
          primary: '#F1F5F9',
          secondary: '#94A3B8',
          muted: '#475569',
        },
      },
      boxShadow: {
        panel: '0 24px 80px rgba(0, 0, 0, 0.45)',
      },
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  safelist: [
    'bg-fuel-cheap',
    'bg-fuel-mid',
    'bg-fuel-expensive',
    'text-fuel-cheap',
    'text-fuel-mid',
    'text-fuel-expensive',
    'border-fuel-cheap',
    'border-fuel-mid',
    'border-fuel-expensive',
  ],
  plugins: [],
};

export default config;
