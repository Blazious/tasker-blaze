import {
  BookOpen,
  CircleEllipsis,
  Home,
  Map,
  Package,
  Printer,
  Shirt,
  Sparkles,
  Utensils,
  WashingMachine,
} from 'lucide-react'

export const CATEGORY_ICON_MAP = {
  laundry: WashingMachine,
  'printing-binding': Printer,
  'food-pickup': Utensils,
  'errand-running': Map,
  thrifting: Shirt,
  'house-cleaning': Sparkles,
  delivery: Package,
  tutoring: BookOpen,
  other: CircleEllipsis,
}

export const CATEGORY_BUDGET_TIPS = {
  laundry: 'KES 150-400',
  'printing-binding': 'KES 50-300',
  'food-pickup': 'KES 100-300',
  'errand-running': 'KES 150-500',
  thrifting: 'KES 200-700',
  'house-cleaning': 'KES 300-1000',
  delivery: 'KES 100-500',
  tutoring: 'KES 300-1500',
  other: 'KES 100-800',
}

export const getCategoryIcon = (slug) => CATEGORY_ICON_MAP[slug] ?? Home
