import React, { useState, useRef, useEffect } from 'react';
import { Sun, Moon, Palette, Check } from 'lucide-react';
import { ThemeId, AccentId } from '../types/wedrop';
import { THEME_OPTIONS, ACCENT_OPTIONS, LAST_THEME_KEYS } from '../utils/status';

interface ThemeSelectorProps {
  currentTheme: ThemeId;
  onSelectTheme: (themeId: ThemeId) => void;
  currentAccent: AccentId;
  onSelectAccent: (accentId: AccentId) => void;
}

export const ThemeSelector: React.FC<ThemeSelectorProps> = ({
  currentTheme,
  onSelectTheme,
  currentAccent,
  onSelectAccent,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const activeThemeObj = THEME_OPTIONS.find((t) => t.id === currentTheme) || THEME_OPTIONS[0];
  const isDarkMode = activeThemeObj.mode === 'dark';

  // Troca de modo: volta para o último tema escolhido no modo oposto
  const handleToggleMode = () => {
    const savedLight = localStorage.getItem(LAST_THEME_KEYS.light) as ThemeId | null;
    const savedDark = localStorage.getItem(LAST_THEME_KEYS.dark) as ThemeId | null;
    if (isDarkMode) {
      onSelectTheme(savedLight || 'light-wedrop');
    } else {
      onSelectTheme(savedDark || 'dark-black');
    }
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const lightThemes = THEME_OPTIONS.filter((t) => t.mode === 'light');
  const darkThemes = THEME_OPTIONS.filter((t) => t.mode === 'dark');

  return (
    <div className="flex items-center gap-1 sm:gap-2 relative" ref={dropdownRef}>
      {/* Quick Mode Toggle Switch (Chavinha Claro / Escuro) */}
      <button
        type="button"
        onClick={handleToggleMode}
        className={`relative inline-flex h-8 w-14 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
          isDarkMode ? 'bg-slate-700 hover:bg-slate-600' : 'bg-slate-200 hover:bg-slate-300'
        }`}
        title={isDarkMode ? 'Alternar para Modo Claro' : 'Alternar para Modo Escuro / Black'}
        aria-label="Alternar tema claro/escuro"
      >
        <span className="sr-only">Alternar tema</span>
        <span
          className={`pointer-events-none flex h-7 w-7 transform items-center justify-center rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
            isDarkMode ? 'translate-x-6 bg-slate-900 text-amber-400' : 'translate-x-0 text-amber-500'
          }`}
        >
          {isDarkMode ? <Moon className="w-3.5 h-3.5 fill-current" /> : <Sun className="w-3.5 h-3.5 fill-current" />}
        </span>
      </button>

      {/* Palette Dropdown Trigger (3 Claros / 3 Escuros) */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 px-2 sm:px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer bg-card border-theme text-theme hover:bg-hover"
        title="Escolher entre os 6 temas visuais (3 claros e 3 escuros)"
      >
        <Palette className="w-3.5 h-3.5 text-accent" />
        <span className="hidden md:inline">{activeThemeObj.name.split(' (')[0]}</span>
      </button>

      {/* Theme Picker Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-72 rounded-xl shadow-2xl border z-50 p-3 bg-card border-theme text-theme">
          <div className="text-[11px] font-bold uppercase tracking-wider text-muted mb-2 px-1">
            Escolha de Tema (6 Modelos)
          </div>

          {/* Section: 3 Temas Claros */}
          <div className="mb-3">
            <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1.5 flex items-center gap-1 px-1">
              <Sun className="w-3 h-3 text-amber-500" />
              <span>3 Modelos Claros</span>
            </div>
            <div className="space-y-1">
              {lightThemes.map((theme) => {
                const isSelected = theme.id === currentTheme;
                return (
                  <button
                    key={theme.id}
                    type="button"
                    onClick={() => {
                      onSelectTheme(theme.id);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center justify-between p-2 rounded-lg text-xs text-left transition-colors ${
                      isSelected
                        ? 'bg-card-secondary text-theme font-semibold ring-1 ring-accent'
                        : 'hover-bg text-theme'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="w-3.5 h-3.5 rounded-full border border-black/10 shrink-0"
                        style={{ backgroundColor: theme.primaryColor }}
                      />
                      <div>
                        <div className="leading-tight">{theme.name}</div>
                        <div className="text-[10px] text-muted font-normal">{theme.description}</div>
                      </div>
                    </div>
                    {isSelected && <Check className="w-3.5 h-3.5 text-accent shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>

          <hr className="border-slate-200 dark:border-slate-700 my-2" />

          {/* Section: 3 Temas Escuros / Pretos */}
          <div>
            <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1.5 flex items-center gap-1 px-1">
              <Moon className="w-3 h-3 text-cyan-400" />
              <span>3 Modelos Escuros / Black</span>
            </div>
            <div className="space-y-1">
              {darkThemes.map((theme) => {
                const isSelected = theme.id === currentTheme;
                return (
                  <button
                    key={theme.id}
                    type="button"
                    onClick={() => {
                      onSelectTheme(theme.id);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center justify-between p-2 rounded-lg text-xs text-left transition-colors ${
                      isSelected
                        ? 'bg-slate-800 text-white font-semibold ring-1 ring-cyan-500'
                        : 'hover:bg-slate-800/60 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="w-3.5 h-3.5 rounded-full border border-white/20 shrink-0"
                        style={{ backgroundColor: theme.primaryColor }}
                      />
                      <div>
                        <div className="leading-tight">{theme.name}</div>
                        <div className="text-[10px] text-slate-400 font-normal">{theme.description}</div>
                      </div>
                    </div>
                    {isSelected && <Check className="w-3.5 h-3.5 text-cyan-400 shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>

          <hr className="border-slate-200 dark:border-slate-700 my-2" />

          {/* Section: cor de destaque (vale para qualquer tema) */}
          <div>
            <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1.5 px-1">
              Cor de destaque
            </div>
            <div className="grid grid-cols-4 gap-1.5">
              {ACCENT_OPTIONS.map((accent) => {
                const isSelected = accent.id === currentAccent;
                return (
                  <button
                    key={accent.id}
                    type="button"
                    onClick={() => onSelectAccent(accent.id)}
                    className={`flex flex-col items-center gap-1 p-1.5 rounded-lg text-[10px] transition-colors ${
                      isSelected ? 'ring-1 ring-accent bg-card-secondary font-semibold' : 'hover:bg-card-secondary'
                    }`}
                    title={accent.name}
                  >
                    <span
                      className="w-5 h-5 rounded-full border border-white/20"
                      style={{
                        background:
                          accent.id === 'tema'
                            ? 'conic-gradient(#ef4444, #10b981, #06b6d4, #8b5cf6, #ef4444)'
                            : accent.color,
                      }}
                    />
                    <span className="leading-tight text-center">{accent.name}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
