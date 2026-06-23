/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Noto Sans SC', 'JetBrains Mono', 'PingFang SC', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        primary: {
          50: '#eef2ff',
          100: '#dbe4ff',
          200: '#bacbff',
          300: '#8ba9ff',
          400: '#667eea',
          500: '#4f6bff',
          600: '#3b50d6',
          700: '#2f3fb3',
          800: '#28348c',
          900: '#232e6e',
        },
        surface: {
          50: '#f8f9fc',
          100: '#f1f2f6',
          200: '#e3e5ed',
          300: '#c5c8d4',
          400: '#9ca0b0',
          500: '#7c8090',
          600: '#5c6070',
          700: '#3c4050',
          800: '#1c1f2e',
          900: '#0d0f1a',
          950: '#07080e',
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.35s ease-out',
        'fade-in-up': 'fadeInUp 0.35s ease-out',
        'pulse-dot': 'pulseDot 1.2s ease-in-out infinite',
        'glow-pulse': 'glowPulse 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%, 80%, 100%': { transform: 'scale(0.6)', opacity: '0.3' },
          '40%': { transform: 'scale(1)', opacity: '1' },
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 8px rgba(102, 126, 234, 0.3)' },
          '50%': { boxShadow: '0 0 20px rgba(102, 126, 234, 0.6)' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
