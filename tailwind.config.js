/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e6f0ff',
          100: '#b3d1ff',
          200: '#80b3ff',
          300: '#4d94ff',
          400: '#1a75ff',
          500: '#4f8cff',
          600: '#0052cc',
          700: '#003d99',
          800: '#002966',
          900: '#001433',
        },
        dark: {
          50: '#3d3d5c',
          100: '#33334d',
          200: '#2a2a3d',
          300: '#21212e',
          400: '#1a1a2e',
          500: '#16162a',
          600: '#121226',
          700: '#0e0e22',
          800: '#0a0a1e',
          900: '#06061a',
        },
        accent: {
          success: '#00d26a',
          warning: '#ffb347',
          error: '#ff6b6b',
        },
      },
    },
  },
  plugins: [],
};
