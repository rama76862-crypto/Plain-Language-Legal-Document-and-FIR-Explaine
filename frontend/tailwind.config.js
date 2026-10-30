/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        bg2: 'var(--bg2)',
        paper: 'var(--paper)',
        ink: 'var(--ink)',
        mute: 'var(--mute)',
        line: 'var(--line)',
        navy: 'var(--navy)',
        blue: 'var(--blue)',
        cyan: 'var(--cyan)',
        concern: {
          DEFAULT: 'var(--concern)',
          bg: 'var(--concern-bg)',
          ink: 'var(--concern-ink)',
        },
        caution: {
          DEFAULT: 'var(--caution)',
          bg: 'var(--caution-bg)',
          ink: 'var(--caution-ink)',
        },
        deadline: {
          DEFAULT: 'var(--deadline)',
          bg: 'var(--deadline-bg)',
          ink: 'var(--deadline-ink)',
        },
        ok: {
          DEFAULT: 'var(--ok)',
          bg: 'var(--ok-bg)',
          ink: 'var(--ok-ink)',
        },
      },
      borderRadius: {
        lg: 'var(--radius-lg)',
        md: 'var(--radius-md)',
        pill: 'var(--radius-pill)',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        pop: 'var(--shadow-pop)',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '"Noto Sans Devanagari"', '"Noto Sans Gurmukhi"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        devanagari: ['"Noto Sans Devanagari"', 'sans-serif'],
        gurmukhi: ['"Noto Sans Gurmukhi"', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
