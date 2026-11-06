/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        ink: '#111827',
        canvas: '#f6f7fb',
        brand: {
          500: '#7c3aed',
          600: '#6d28d9',
        },
      },
      boxShadow: {
        card: '0 12px 30px rgba(15, 23, 42, 0.06)',
      },
    },
  },
  plugins: [],
}
