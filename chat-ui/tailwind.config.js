/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Noto Sans SC', 'PingFang SC', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: {
          50: '#f0f4ff',
          100: '#dbe5ff',
          200: '#baceff',
          300: '#8dacff',
          400: '#6b8cff',
          500: '#4f6bff',
          600: '#3b4fdb',
          700: '#2f3fb3',
          800: '#28348c',
          900: '#232e6e',
        },
        doubao: {
          start: '#4f6bff',
          mid: '#7c5cfc',
          end: '#a855f7',
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.35s ease-out',
        'fade-in-up': 'fadeInUp 0.35s ease-out',
        'pulse-dot': 'pulseDot 1.2s ease-in-out infinite',
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
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
