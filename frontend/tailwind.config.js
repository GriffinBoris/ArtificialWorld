import forms from "@tailwindcss/forms";

const semanticColor = (tokenName) => `rgb(var(${tokenName}) / <alpha-value>)`;

export default {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: ["./src/**/*.{ts,tsx,vue}", "./index.html"],
  theme: {
    extend: {
      colors: {
        background: semanticColor("--color-background"),
        surface: semanticColor("--color-surface"),
        "surface-muted": semanticColor("--color-surface-muted"),
        body: semanticColor("--color-body"),
        secondary: semanticColor("--color-secondary"),
        line: semanticColor("--color-line"),
        primary: semanticColor("--color-primary"),
        "primary-contrast": semanticColor("--color-primary-contrast"),
        "focus-ring": semanticColor("--color-focus-ring"),
        success: semanticColor("--color-success"),
        warning: semanticColor("--color-warning"),
        error: semanticColor("--color-error"),
        info: semanticColor("--color-info"),
      },
      fontFamily: {
        sans: ['"Inter"', '"Public Sans"', "system-ui", "-apple-system", "sans-serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
      },
      fontSize: {
        "base-body": ["var(--font-size-base)", { lineHeight: "var(--line-height-base)" }],
        muted: ["var(--font-size-muted)", { lineHeight: "var(--line-height-muted)" }],
        control: ["var(--font-size-control)", { lineHeight: "var(--line-height-control)" }],
        "table-header": ["var(--font-size-table-header)", { lineHeight: "var(--line-height-table-header)" }],
        "heading-sm": ["var(--font-size-heading-sm)", { lineHeight: "var(--line-height-heading-sm)" }],
        "heading-lg": ["var(--font-size-heading-lg)", { lineHeight: "var(--line-height-heading-lg)" }],
        metric: ["var(--font-size-metric)", { lineHeight: "var(--line-height-metric)" }],
        eyebrow: [
          "var(--font-size-eyebrow)",
          { lineHeight: "var(--line-height-eyebrow)", letterSpacing: "var(--tracking-eyebrow)" },
        ],
      },
    },
  },
  plugins: [forms],
};
