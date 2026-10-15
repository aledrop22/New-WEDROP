import { AccentOption, ThemeOption } from '../types/wedrop';
import { APP_TIME_ZONE, daysBetween, dayKeyFromDate, shiftDayKey, todayKey } from './dates';

export const CATEGORY_NAMES = [
  "Cozinha",
  "Organização",
  "Limpeza e Lavanderia",
  "Banheiro",
  "Decoração e Têxteis",
  "Eletroportáteis",
  "Brinquedos",
  "Papelaria e Escritório",
  "Ferramentas e Automotivo",
  "Esporte e Lazer",
  "Pets",
  "Beleza e Cuidado Pessoal",
  "Moda, Malas e Acessórios",
  "Natal e Festas",
] as const;

export const THEME_OPTIONS: ThemeOption[] = [
  // 3 Temas Claros
  {
    id: 'light-wedrop',
    name: 'WeDrop Clean (Claro)',
    mode: 'light',
    description: 'Branco nítido com vermelho WeDrop e ardósia clássico.',
    primaryColor: '#e02424',
    badgeBg: 'bg-red-500',
  },
  {
    id: 'light-emerald',
    name: 'Executivo Esmeralda (Claro)',
    mode: 'light',
    description: 'Branco níveo com acentos esmeralda e visual corporativo.',
    primaryColor: '#059669',
    badgeBg: 'bg-emerald-600',
  },
  {
    id: 'light-amber',
    name: 'Areia & Âmbar (Claro)',
    mode: 'light',
    description: 'Tom marfim suave com toques quentes de âmbar e bronze.',
    primaryColor: '#d97706',
    badgeBg: 'bg-amber-600',
  },
  // 3 Temas Escuros / Pretos
  {
    id: 'dark-onyx',
    name: 'WeDrop Carmesim (Escuro)',
    mode: 'dark',
    description: 'Grafite profundo ônix (#0f172a) com vermelho carmesim.',
    primaryColor: '#ef4444',
    badgeBg: 'bg-red-500',
  },
  {
    id: 'dark-black',
    name: 'True Black OLED (Preto Puro)',
    mode: 'dark',
    description: 'Preto puro (#000000) com contraste máximo e neon esmeralda.',
    primaryColor: '#10b981',
    badgeBg: 'bg-emerald-500',
  },
  {
    id: 'dark-midnight',
    name: 'Midnight Blue & Ciano (Escuro)',
    mode: 'dark',
    description: 'Azul noite profundo com acentos ciano elétrico brilhante.',
    primaryColor: '#06b6d4',
    badgeBg: 'bg-cyan-500',
  },
];

/** Último tema escolhido em cada modo: a chave claro/escuro volta para ele. */
export const LAST_THEME_KEYS = {
  light: 'wedrop_last_light',
  dark: 'wedrop_last_dark',
} as const;

/** Cores de destaque selecionáveis. 'tema' mantém a cor que o tema define. */
export const ACCENT_OPTIONS: AccentOption[] = [
  { id: 'tema', name: 'Padrão do tema', color: '', hover: '' },
  { id: 'vermelho', name: 'Vermelho', color: '#ef4444', hover: '#dc2626' },
  { id: 'esmeralda', name: 'Esmeralda', color: '#10b981', hover: '#059669' },
  { id: 'ciano', name: 'Ciano', color: '#06b6d4', hover: '#0891b2' },
  { id: 'azul', name: 'Azul', color: '#3b82f6', hover: '#2563eb' },
  { id: 'violeta', name: 'Violeta', color: '#8b5cf6', hover: '#7c3aed' },
  { id: 'rosa', name: 'Rosa', color: '#ec4899', hover: '#db2777' },
  { id: 'ambar', name: 'Âmbar', color: '#f59e0b', hover: '#d97706' },
];

export function normalizeText(text: string | null | undefined): string {
  if (!text) return "";
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .trim()
    .toLowerCase();
}

export function statusFromAvailability(availability: string | null | undefined): string {
  const plain = normalizeText(availability);
  if (plain === "disponivel") return "Ativo";
  if (plain === "indisponivel") return "Inativo";
  return "";
}

export function effectiveStatus(isActive: string | null | undefined, availability: string | null | undefined): string {
  return (isActive || "").trim() || statusFromAvailability(availability);
}

export function getStatusBucket(isActive: string | null | undefined, availability?: string | null | undefined): 'Ativos' | 'Inativos' | 'Sem status' {
  const eff = effectiveStatus(isActive, availability);
  const normalized = normalizeText(eff);

  if (
    normalized.includes("inativ") ||
    normalized.includes("desativ") ||
    normalized.includes("inactive") ||
    normalized.includes("disabled") ||
    ["false", "0", "nao", "não"].includes(normalized)
  ) {
    return "Inativos";
  }

  if (["ativo", "active", "true", "1", "sim"].includes(normalized) || normalized.includes("ativo")) {
    return "Ativos";
  }

  return "Sem status";
}

export function formatInt(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("pt-BR").format(value);
}

export function parsePriceNumber(priceStr: string | null | undefined): number {
  if (!priceStr) return 0;
  const cleaned = priceStr.replace(/[^0-9,-]/g, "").replace(",", ".");
  const val = parseFloat(cleaned);
  return isNaN(val) ? 0 : val;
}

export function formatCurrency(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") {
    if (value.startsWith("R$")) return value;
    const num = parseFloat(value.replace(/[^0-9,-]/g, "").replace(",", "."));
    if (!isNaN(num)) {
      return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(num);
    }
    return value;
  }
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
}

/** Aceita "AAAA-MM-DD" (sem conversão de fuso) ou uma data completa. */
export function formatDateBR(dateString: string | null | undefined): string {
  if (!dateString) return "—";
  const dayMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateString);
  if (dayMatch) return `${dayMatch[3]}/${dayMatch[2]}/${dayMatch[1]}`;
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString("pt-BR", { timeZone: APP_TIME_ZONE });
  } catch {
    return dateString;
  }
}

export function formatDateTimeBR(dateString: string | null | undefined): string {
  if (!dateString) return "—";
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    const date = d.toLocaleDateString("pt-BR", { timeZone: APP_TIME_ZONE });
    const time = d.toLocaleTimeString("pt-BR", { timeZone: APP_TIME_ZONE, hour: '2-digit', minute: '2-digit' });
    return `${date} às ${time}`;
  } catch {
    return dateString;
  }
}

/** Dia atual (AAAA-MM-DD) no fuso de São Paulo, não no fuso do navegador. */
export function getLocalDateString(d: Date = new Date()): string {
  return dayKeyFromDate(d);
}

export function getPastDate(daysAgo: number): string {
  return shiftDayKey(todayKey(), -daysAgo);
}

export function generateDaysRange(startDateStr: string, endDateStr: string): string[] {
  return daysBetween(startDateStr, endDateStr);
}

export function formatDayToDDMM(isoDate: string): string {
  try {
    const parts = isoDate.split("-");
    if (parts.length === 3) {
      return `${parts[2]}/${parts[1]}`;
    }
    return isoDate;
  } catch {
    return isoDate;
  }
}

export const WITHOUT_STATUS_HELP =
  "Produto salvo sem o selo Disponível/Indisponível: a página foi lida antes do cabeçalho (nome, preço e selo) carregar. A próxima coleta relê esses produtos por inteiro.";
