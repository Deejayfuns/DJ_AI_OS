/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0a0f',
        panel: '#14141c',
        card: '#1a1a24',
        accent: '#ff3b3b',
        'accent-hover': '#ef2b2b',
        muted: '#8b8b9a',
        text: '#e5e5ea',
        success: '#34d399',
        warning: '#fbbf24',
        danger: '#f87171',
      },
      fontFamily: {
        sans: ['Segoe UI', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
