import { useState, useEffect } from 'react';

export type Theme = 'dark' | 'light';

const THEME_STORAGE_KEY = 'bitcoin_intel_theme';

export function getInitialTheme(): Theme {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === 'light' || saved === 'dark') {
      return saved;
    }
  } catch {
    // localStorage not accessible
  }
  return 'dark';
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // localStorage not accessible
  }
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  return { theme, toggleTheme, setTheme };
}
