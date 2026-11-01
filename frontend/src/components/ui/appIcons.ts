import {
  CircleCheckBig,
  Globe,
  House,
  Info,
  LogOut,
  type LucideIcon,
  Menu,
  Moon,
  Plus,
  RefreshCw,
  Search,
  Settings,
  Sun,
  TriangleAlert,
  X,
} from "@lucide/vue";

export const appIcons = {
  close: X,
  dashboard: House,
  globe: Globe,
  info: Info,
  logout: LogOut,
  menu: Menu,
  moon: Moon,
  plus: Plus,
  refresh: RefreshCw,
  search: Search,
  settings: Settings,
  success: CircleCheckBig,
  sun: Sun,
  warning: TriangleAlert,
} satisfies Record<string, LucideIcon>;

export type AppIconName = keyof typeof appIcons;
