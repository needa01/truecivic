# 🏛️ TrueCivic Platform — Design Specification

**Version:** 1.0  
**Last Updated:** October 19, 2025  
**Status:** Initial Design Phase

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Design Philosophy](#design-philosophy)
3. [Visual Design System](#visual-design-system)
4. [Component Architecture](#component-architecture)
5. [Page-Specific Designs](#page-specific-designs)
6. [Responsive & Mobile Strategy](#responsive--mobile-strategy)
7. [Accessibility & Performance](#accessibility--performance)
8. [Technical Implementation Notes](#technical-implementation-notes)

---

## 🎯 Executive Summary

TrueCivic is a modern parliamentary transparency platform featuring a **liquid glass morphism** design aesthetic. The platform provides comprehensive access to Canadian federal legislative data across Bills, Votes, Debates, Committee Meetings, and Member profiles.

**Key Design Pillars:**
- **Transparency:** Clear data hierarchy with intuitive filtering
- **Accessibility:** WCAG 2.1 AA compliant, keyboard navigable
- **Performance:** <2s initial load, optimistic UI updates
- **Elegance:** Liquid glass aesthetic with smooth micro-interactions

---

## 🎨 Design Philosophy

### Visual Identity

**Core Aesthetic: Liquid Glass Morphism**

The design leverages glassmorphism with fluid, organic transitions:

- **Frosted glass cards** with subtle blur (`backdrop-filter: blur(16px)`)
- **Gradient borders** that shift on hover
- **Liquid transitions** using cubic-bezier easing
- **Depth through layering** (shadow hierarchy)

**Color Psychology:**
- **Liberal Red:** `#DC2626` (warm, progressive)
- **Conservative Blue:** `#2563EB` (stable, traditional)
- **NDP Orange:** `#F59E0B` (energetic, populist)
- **Green:** `#10B981` (environmental, balanced)
- **Bloc Québécois:** `#06B6D4` (distinct, regional)

---

## 🎨 Visual Design System

### Color Palette

#### Light Theme
```css
:root[data-theme="light"] {
  /* Primary Surface */
  --surface-primary: rgba(255, 255, 255, 0.75);
  --surface-secondary: rgba(249, 250, 251, 0.85);
  --surface-tertiary: rgba(243, 244, 246, 0.90);
  
  /* Glass Effects */
  --glass-border: rgba(229, 231, 235, 0.5);
  --glass-shadow: rgba(0, 0, 0, 0.05);
  --glass-blur: blur(16px);
  
  /* Text Hierarchy */
  --text-primary: #111827;
  --text-secondary: #4B5563;
  --text-tertiary: #9CA3AF;
  
  /* Accent Colors */
  --accent-liberal: #DC2626;
  --accent-conservative: #2563EB;
  --accent-ndp: #F59E0B;
  --accent-green: #10B981;
  --accent-bloc: #06B6D4;
  
  /* Status Colors */
  --status-active: #10B981;
  --status-pending: #F59E0B;
  --status-completed: #6366F1;
  --status-failed: #EF4444;
}
```

#### Dark Theme
```css
:root[data-theme="dark"] {
  /* Primary Surface */
  --surface-primary: rgba(17, 24, 39, 0.75);
  --surface-secondary: rgba(31, 41, 55, 0.85);
  --surface-tertiary: rgba(55, 65, 81, 0.90);
  
  /* Glass Effects */
  --glass-border: rgba(75, 85, 99, 0.3);
  --glass-shadow: rgba(0, 0, 0, 0.3);
  --glass-blur: blur(20px);
  
  /* Text Hierarchy */
  --text-primary: #F9FAFB;
  --text-secondary: #D1D5DB;
  --text-tertiary: #6B7280;
  
  /* Accent Colors (slightly desaturated) */
  --accent-liberal: #EF4444;
  --accent-conservative: #3B82F6;
  --accent-ndp: #FBBF24;
  --accent-green: #34D399;
  --accent-bloc: #22D3EE;
}
```

### Typography

**Font Stack:**
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

**Type Scale:**
```css
--text-xs: 0.75rem;    /* 12px - metadata, labels */
--text-sm: 0.875rem;   /* 14px - body small, captions */
--text-base: 1rem;     /* 16px - body text */
--text-lg: 1.125rem;   /* 18px - emphasized body */
--text-xl: 1.25rem;    /* 20px - card titles */
--text-2xl: 1.5rem;    /* 24px - section headers */
--text-3xl: 1.875rem;  /* 30px - page headers */
--text-4xl: 2.25rem;   /* 36px - hero text */
```

**Font Weights:**
```css
--weight-normal: 400;
--weight-medium: 500;
--weight-semibold: 600;
--weight-bold: 700;
```

### Spacing System

**8pt Grid System:**
```css
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
--space-24: 6rem;     /* 96px */
```

### Border Radius

```css
--radius-sm: 0.375rem;   /* 6px - small elements */
--radius-md: 0.5rem;     /* 8px - cards, buttons */
--radius-lg: 0.75rem;    /* 12px - modals */
--radius-xl: 1rem;       /* 16px - hero cards */
--radius-2xl: 1.5rem;    /* 24px - feature sections */
--radius-full: 9999px;   /* Pills, avatars */
```

### Shadows

```css
/* Light Theme */
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);

/* Dark Theme */
--shadow-sm-dark: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
--shadow-md-dark: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
--shadow-lg-dark: 0 10px 15px -3px rgba(0, 0, 0, 0.6);
--shadow-xl-dark: 0 20px 25px -5px rgba(0, 0, 0, 0.7);
```

---

## 🧩 Component Architecture

### Global Navigation Header

**Structure:**
```
┌────────────────────────────────────────────────────────┐
│ [Logo] Bills Votes Debates Meetings Members   [🌙][📅] │
└────────────────────────────────────────────────────────┘
```

**Specifications:**
- **Height:** `64px` (desktop), `56px` (mobile)
- **Background:** Glass surface with `backdrop-filter: blur(20px)`
- **Position:** Sticky top with slide-down animation
- **Active State:** Bottom border accent (2px, party color)

**Component Breakdown:**

```typescript
// NavHeader.tsx
interface NavHeaderProps {
  activeSection: 'bills' | 'votes' | 'debates' | 'meetings' | 'members';
  theme: 'light' | 'dark';
  onThemeToggle: () => void;
  parliamentSession: string;
}
```

**CSS Implementation:**
```css
.nav-header {
  position: sticky;
  top: 0;
  z-index: 50;
  height: 64px;
  padding: 0 var(--space-6);
  
  background: var(--surface-primary);
  backdrop-filter: var(--glass-blur);
  border-bottom: 1px solid var(--glass-border);
  box-shadow: var(--shadow-md);
  
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.nav-header.scrolled-up {
  transform: translateY(-100%);
}

.nav-link {
  position: relative;
  padding: var(--space-3) var(--space-4);
  font-weight: var(--weight-medium);
  color: var(--text-secondary);
  transition: color 0.2s ease;
}

.nav-link.active {
  color: var(--text-primary);
}

.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent-liberal), var(--accent-conservative));
  animation: slide-in 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slide-in {
  from { transform: scaleX(0); }
  to { transform: scaleX(1); }
}
```

---

### Filter Bar Component

**Layout:**
```
┌────────────────────────────────────────────────────────┐
│ [Jurisdiction ▼] [Chamber ▼] [Status ▼] [Type ▼] [🔍] │
└────────────────────────────────────────────────────────┘
```

**Specifications:**
- **Height:** `56px`
- **Spacing:** `16px` gap between filters
- **Sticky:** Below header on scroll
- **Animation:** Slide-in from top (200ms delay after header)

```typescript
// FilterBar.tsx
interface FilterBarProps {
  jurisdiction: string[];
  chamber?: string[];
  status?: string[];
  type?: string[];
  onFilterChange: (filters: FilterState) => void;
}
```

**CSS Implementation:**
```css
.filter-bar {
  position: sticky;
  top: 64px;
  z-index: 40;
  
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-6);
  
  background: var(--surface-secondary);
  backdrop-filter: var(--glass-blur);
  border-bottom: 1px solid var(--glass-border);
  
  animation: slide-down 0.4s cubic-bezier(0.4, 0, 0.2, 1) 0.2s both;
}

@keyframes slide-down {
  from {
    transform: translateY(-100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.filter-dropdown {
  position: relative;
  min-width: 140px;
}

.filter-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  
  padding: var(--space-2) var(--space-3);
  
  background: var(--surface-primary);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
  
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-trigger:hover {
  border-color: var(--accent-conservative);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.filter-menu {
  position: absolute;
  top: calc(100% + var(--space-2));
  left: 0;
  z-index: 50;
  
  min-width: 200px;
  padding: var(--space-2);
  
  background: var(--surface-primary);
  backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  
  animation: scale-in 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes scale-in {
  from {
    transform: scale(0.95);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
```

---

### Glass Card Component

**Base Card Structure:**

```typescript
// GlassCard.tsx
interface GlassCardProps {
  variant: 'bill' | 'vote' | 'debate' | 'meeting' | 'member';
  data: CardData;
  onClick?: () => void;
}
```

**CSS Implementation:**
```css
.glass-card {
  position: relative;
  padding: var(--space-6);
  
  background: var(--surface-primary);
  backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-xl);
  
  box-shadow: var(--shadow-md);
  
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.glass-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-xl);
  border-color: rgba(37, 99, 235, 0.3);
}

.glass-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-xl);
  padding: 1px;
  background: linear-gradient(135deg, 
    rgba(255,255,255,0.3), 
    rgba(255,255,255,0)
  );
  -webkit-mask: 
    linear-gradient(#fff 0 0) content-box, 
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.glass-card:hover::before {
  opacity: 1;
}

/* Party Accent Border */
.glass-card[data-party="liberal"]::after {
  content: '';
  position: absolute;
  left: 0;
  top: var(--space-4);
  bottom: var(--space-4);
  width: 3px;
  background: var(--accent-liberal);
  border-radius: var(--radius-full);
}

.glass-card[data-party="conservative"]::after {
  background: var(--accent-conservative);
}

.glass-card[data-party="ndp"]::after {
  background: var(--accent-ndp);
}
```

---

### Bill Card Component

**Visual Structure:**
```
┌────────────────────────────────────────────┐
│ [C-11] An Act to amend...          [●●●]  │
│ Liberal • House • First Reading            │
│ Sponsor: Hon. Pablo Rodriguez             │
│ Last Activity: 2 days ago                  │
│                                            │
│ [📄 Summary] [🗣️ 12 Debates] [🗳️ 3 Votes] │
└────────────────────────────────────────────┘
```

```css
.bill-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.bill-label {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-3);
  
  background: linear-gradient(135deg, 
    rgba(37, 99, 235, 0.1), 
    rgba(37, 99, 235, 0.05)
  );
  border: 1px solid rgba(37, 99, 235, 0.2);
  border-radius: var(--radius-full);
  
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--accent-conservative);
  letter-spacing: 0.5px;
}

.bill-title {
  margin-top: var(--space-2);
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  line-height: 1.4;
}

.bill-meta {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-3);
  
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.bill-meta-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.bill-meta-item::before {
  content: '•';
  color: var(--text-tertiary);
}

.bill-meta-item:first-child::before {
  display: none;
}

.bill-actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--glass-border);
}

.bill-action-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  
  background: var(--surface-secondary);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-secondary);
  
  cursor: pointer;
  transition: all 0.2s ease;
}

.bill-action-btn:hover {
  background: var(--surface-tertiary);
  color: var(--text-primary);
  border-color: var(--accent-conservative);
}
```

---

### Status Badge Component

```typescript
// StatusBadge.tsx
interface StatusBadgeProps {
  status: 'active' | 'pending' | 'completed' | 'failed' | 'first-reading' | 'second-reading' | 'third-reading' | 'royal-assent';
  size?: 'sm' | 'md' | 'lg';
}
```

```css
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Status Variants */
.status-badge[data-status="active"] {
  background: rgba(16, 185, 129, 0.1);
  color: var(--status-active);
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.status-badge[data-status="active"]::before {
  background: var(--status-active);
}

.status-badge[data-status="pending"] {
  background: rgba(245, 158, 11, 0.1);
  color: var(--status-pending);
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.status-badge[data-status="pending"]::before {
  background: var(--status-pending);
}
```

---

## 📄 Page-Specific Designs

### 1. Bills Page

**Layout Grid:**
```
┌─────────────────────────────────────────────────────┐
│ Header (Bills) + Filters                            │
├─────────────────────────────────────────────────────┤
│ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐           │
│ │ Card  │ │ Card  │ │ Card  │ │ Card  │  (4 cols) │
│ └───────┘ └───────┘ └───────┘ └───────┘           │
│ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐           │
│ │ Card  │ │ Card  │ │ Card  │ │ Card  │           │
│ └───────┘ └───────┘ └───────┘ └───────┘           │
├─────────────────────────────────────────────────────┤
│ [Show More] Pagination • Last Sync: 2 mins ago     │
└─────────────────────────────────────────────────────┘
```

**Filter Options:**
- **Jurisdiction:** Federal (House/Senate), Provincial (future)
- **Chamber:** House of Commons, Senate
- **Status:** First Reading, Second Reading, Third Reading, Royal Assent, Dropped
- **Bill Type:** Government Bill, Private Member's Bill, Senate Bill
- **Sponsor:** All MPs/Senators (searchable dropdown)
- **Date Range:** Newest, This Week, This Month, This Session

**Responsive Breakpoints:**
- **Desktop (≥1280px):** 4 columns
- **Tablet (768-1279px):** 2 columns
- **Mobile (<768px):** 1 column

```css
.bills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-6);
  padding: var(--space-6);
}

@media (min-width: 1280px) {
  .bills-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (min-width: 768px) and (max-width: 1279px) {
  .bills-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 767px) {
  .bills-grid {
    grid-template-columns: 1fr;
    padding: var(--space-4);
    gap: var(--space-4);
  }
}
```

---

### 2. Bill Detail Page

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│ ← Back to Bills                                     │
├─────────────────────────────────────────────────────┤
│ [C-11] An Act to amend the Broadcasting Act         │
│ Liberal • House • Second Reading                    │
│                                                     │
│ ┌─────────────────────┐ ┌───────────────────────┐ │
│ │ 📄 Summary          │ │ 📊 Status Timeline    │ │
│ │ (AI-Generated)      │ │                       │ │
│ │ ⚠️ Caution warning  │ │ ● First Reading      │ │
│ │                     │ │ ● Second Reading     │ │
│ │ [View Full Text]    │ │ ○ Third Reading      │ │
│ └─────────────────────┘ └───────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐│
│ │ 👤 Sponsor: Hon. Pablo Rodriguez               ││
│ │ Liberal • Minister of Canadian Heritage        ││
│ └─────────────────────────────────────────────────┘│
│                                                     │
│ ┌─────────────────────────────────────────────────┐│
│ │ 🗣️ Debate Mentions (12)                        ││
│ │ ┌─────────────────────────────────────────────┐││
│ │ │ Debate on C-11 - Feb 14, 2025              │││
│ │ │ 47 interventions • 3 hours                 │││
│ │ └─────────────────────────────────────────────┘││
│ └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

**AI Summary Component:**
```css
.ai-summary-card {
  position: relative;
  padding: var(--space-6);
  background: linear-gradient(135deg, 
    rgba(99, 102, 241, 0.05), 
    rgba(139, 92, 246, 0.03)
  );
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: var(--radius-xl);
}

.ai-summary-card::before {
  content: '🤖 AI Summary';
  display: block;
  margin-bottom: var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--accent-conservative);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ai-caution {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding: var(--space-3);
  
  background: rgba(245, 158, 11, 0.1);
  border-left: 3px solid var(--status-pending);
  border-radius: var(--radius-md);
  
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
```

---

### 3. Votes Page

**Filter Options:**
- **Member:** All MPs (searchable)
- **Vote Type:** Recorded Division, Voice Vote, Standing Vote
- **Date Range:** Last 7 days, Last 30 days, This Session
- **Result:** Passed, Failed, Tied

**Vote Card Structure:**
```
┌────────────────────────────────────────────┐
│ Motion to Amend Bill C-11                  │
│ Recorded Division • Feb 15, 2025           │
│                                            │
│ Result: PASSED                             │
│ ✓ 178  ✗ 145  ○ 15                        │
│                                            │
│ [View Full Results] [View Debate]         │
└────────────────────────────────────────────┘
```

```css
.vote-result {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin: var(--space-4) 0;
  padding: var(--space-4);
  
  background: var(--surface-secondary);
  border-radius: var(--radius-lg);
}

.vote-count {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
}

.vote-count[data-type="yea"] {
  color: var(--status-active);
}

.vote-count[data-type="nay"] {
  color: var(--status-failed);
}

.vote-count[data-type="abstain"] {
  color: var(--text-tertiary);
}
```

---

### 4. Debates Page

**Filter Options:**
- **Bills Discussed:** All, Specific Bill
- **Intervention Type:** Question, Statement, Point of Order, Response
- **Participating MPs:** All MPs (multi-select)
- **Date Range:** Last 7 days, Last 30 days, This Session

**Debate Card:**
```
┌────────────────────────────────────────────┐
│ Debate on Bill C-11                        │
│ Feb 14, 2025 • 14:30 - 17:45              │
│                                            │
│ 47 interventions • 12 MPs participated     │
│                                            │
│ Top Speakers:                              │
│ • Hon. Pablo Rodriguez (Liberal) - 8      │
│ • Pierre Poilievre (Conservative) - 6     │
│                                            │
│ [View Transcript] [View Summary]          │
└────────────────────────────────────────────┘
```

---

### 5. Meetings Page

**Similar structure to Debates with additional filters:**
- **Committee:** All Committees (dropdown)
- **Meeting Type:** Regular, Special, Emergency
- **Witnesses:** Name search
- **Topics:** Keywords/tags

---

### 6. Members Page

**Grid Layout:**
```
┌─────────────────────────────────────────────────────┐
│ Filters: [Federal ▼] [Party ▼] [Province ▼]       │
├─────────────────────────────────────────────────────┤
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│ │ Avatar │ │ Avatar │ │ Avatar │ │ Avatar │       │
│ │ Name   │ │ Name   │ │ Name   │ │ Name   │       │
│ │ Party  │ │ Party  │ │ Party  │ │ Party  │       │
│ │ Bills:5│ │ Bills:3│ │ Bills:8│ │ Bills:2│       │
│ │ Votes  │ │ Votes  │ │ Votes  │ │ Votes  │       │
│ └────────┘ └────────┘ └────────┘ └────────┘       │
└─────────────────────────────────────────────────────┘
```

**Member Card:**
```css
.member-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-6);
  text-align: center;
}

.member-avatar {
  width: 96px;
  height: 96px;
  margin-bottom: var(--space-4);
  
  border-radius: var(--radius-full);
  border: 3px solid var(--glass-border);
  box-shadow: var(--shadow-lg);
  
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.member-card:hover .member-avatar {
  transform: scale(1.1);
  border-color: var(--accent-conservative);
}

.member-stats {
  display: flex;
  justify-content: space-around;
  width: 100%;
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--glass-border);
}

.member-stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.member-stat-value {
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
}

.member-stat-label {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  text-transform: uppercase;
}
```

---

### 7. Member Detail Page

**Layout Sections:**

1. **Profile Header**
```
┌─────────────────────────────────────────────────────┐
│ [Avatar] Hon. Pablo Rodriguez                      │
│          Liberal • Minister of Canadian Heritage   │
│          Honoré-Mercier, Quebec                    │
│                                                     │
│ Bills: 12  Votes With: 87%  Votes Against: 13%    │
└─────────────────────────────────────────────────────┘
```

2. **Activity Summary** (Timeline visualization)
3. **Contact Information**
4. **Committee Memberships** (Cards)
5. **Voting Record** (Table with filters)
6. **Bills Sponsored** (List with status)
7. **Debate Interventions** (Paginated list)
8. **Committee Interventions** (Paginated list)
9. **Associations/Groups** (Tags)
10. **Constituency History** (Timeline)
11. **Caucus History** (Timeline)
12. **Election History** (Timeline with vote percentages)

```css
.member-detail-header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-8);
  padding: var(--space-8);
  
  background: linear-gradient(135deg, 
    var(--surface-primary), 
    var(--surface-secondary)
  );
  border-radius: var(--radius-2xl);
}

.member-detail-avatar {
  width: 160px;
  height: 160px;
  border-radius: var(--radius-full);
  border: 4px solid var(--glass-border);
  box-shadow: var(--shadow-xl);
}

.member-detail-info {
  flex: 1;
}

.member-detail-name {
  font-size: var(--text-4xl);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.member-detail-role {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  margin-bottom: var(--space-1);
}

.member-detail-constituency {
  font-size: var(--text-base);
  color: var(--text-tertiary);
}

.member-stats-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-6);
  margin-top: var(--space-8);
}

.member-stat-card {
  padding: var(--space-6);
  background: var(--surface-primary);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-xl);
  text-align: center;
}
```

---

## 📱 Responsive & Mobile Strategy

### Breakpoint System

```css
/* Mobile First Approach */
:root {
  --container-sm: 640px;
  --container-md: 768px;
  --container-lg: 1024px;
  --container-xl: 1280px;
  --container-2xl: 1536px;
}
```

### Mobile Optimizations

**1. Navigation (Mobile)**
```
┌────────────────────────────┐
│ [☰] TrueCivic        [🌙] │
├────────────────────────────┤
│ Expanded Menu:             │
│ ✓ Bills                    │
│   Votes                    │
│   Debates                  │
│   Meetings                 │
│   Members                  │
│   Parliament: 44-1      ▼  │
└────────────────────────────┘
```

```css
.mobile-nav {
  display: none;
}

@media (max-width: 767px) {
  .desktop-nav {
    display: none;
  }
  
  .mobile-nav {
    display: flex;
  }
  
  .mobile-menu {
    position: fixed;
    top: 56px;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 40;
    
    background: var(--surface-primary);
    backdrop-filter: var(--glass-blur);
    
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  
  .mobile-menu.open {
    transform: translateX(0);
  }
}
```

**2. Filter Bar (Mobile)**
- Collapse filters into "Filter" button
- Show bottom sheet modal with all filters
- Apply/Clear actions at bottom

**3. Card Layout (Mobile)**
- Stack all content vertically
- Increase touch targets to 44x44px minimum
- Reduce font sizes by 1 step
- Simplify metadata display

**4. Pagination (Mobile)**
- Replace numbered pagination with "Load More" button
- Implement infinite scroll (optional)
- Show "XX of YYY results" counter

---

## ♿ Accessibility & Performance

### WCAG 2.1 AA Compliance

**Color Contrast:**
- Text on background: ≥4.5:1 (AA)
- Large text: ≥3:1
- UI components: ≥3:1

**Keyboard Navigation:**
- All interactive elements keyboard accessible
- Focus indicators: 2px outline with high contrast
- Skip links for main content
- Logical tab order

**Screen Reader Support:**
- ARIA labels on all icons
- Role attributes for custom components
- Live regions for dynamic content
- Alt text for all images

```css
/* Focus Styles */
*:focus-visible {
  outline: 2px solid var(--accent-conservative);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  padding: var(--space-2) var(--space-4);
  background: var(--surface-primary);
  color: var(--text-primary);
  text-decoration: none;
  z-index: 100;
}

.skip-link:focus {
  top: 0;
}
```

### Performance Targets

- **First Contentful Paint (FCP):** <1.5s
- **Largest Contentful Paint (LCP):** <2.5s
- **Time to Interactive (TTI):** <3.5s
- **Cumulative Layout Shift (CLS):** <0.1
- **First Input Delay (FID):** <100ms

**Optimization Strategies:**
1. **Lazy Loading:** Images, cards below fold
2. **Code Splitting:** Route-based chunks
3. **Prefetching:** Next page data on hover
4. **Caching:** Service Worker for API responses
5. **Image Optimization:** WebP format, responsive images
6. **Font Loading:** `font-display: swap`

---

## 🔧 Technical Implementation Notes

### Framework Stack

**Frontend:**
- **Next.js 14+** (App Router)
- **React 18+** (Server Components where possible)
- **TypeScript 5+** (Strict mode)
- **Tailwind CSS 3+** (Custom theme)
- **Framer Motion** (Animations)
- **Radix UI** (Accessible primitives)

**State Management:**
- **Zustand** (Global state)
- **TanStack Query** (Server state)
- **React Hook Form** (Forms)

**Testing:**
- **Vitest** (Unit tests)
- **Testing Library** (Component tests)
- **Playwright** (E2E tests)
- **Axe** (Accessibility testing)

### CSS Architecture

**Approach:** Hybrid (Tailwind + CSS Modules)

```
styles/
├── globals.css          # Theme variables, resets
├── themes/
│   ├── light.css
│   └── dark.css
├── components/          # Component-specific modules
│   ├── GlassCard.module.css
│   ├── FilterBar.module.css
│   └── ...
└── utilities/           # Utility classes
    ├── animations.css
    └── shadows.css
```

### Animation Library

```css
/* Liquid Glass Transitions */
@keyframes liquid-morph {
  0%, 100% {
    border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%;
  }
  50% {
    border-radius: 30% 60% 70% 40% / 50% 60% 30% 60%;
  }
}

/* Shimmer Loading */
@keyframes shimmer {
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
}

.loading-shimmer {
  background: linear-gradient(
    90deg,
    var(--surface-secondary) 0%,
    var(--surface-tertiary) 50%,
    var(--surface-secondary) 100%
  );
  background-size: 1000px 100%;
  animation: shimmer 2s infinite;
}

/* Stagger Children */
.stagger-container > * {
  animation: fade-in-up 0.5s cubic-bezier(0.4, 0, 0.2, 1) both;
}

.stagger-container > *:nth-child(1) { animation-delay: 0.1s; }
.stagger-container > *:nth-child(2) { animation-delay: 0.2s; }
.stagger-container > *:nth-child(3) { animation-delay: 0.3s; }
/* ... continue for n children */

@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

---

## 📊 Footer & Pagination

### Footer Component

```
┌─────────────────────────────────────────────────────┐
│ Last Synced: 2 minutes ago • Showing 25 of 1,247   │
│ [25 ▼] per page                    [< 1 2 3 ... >] │
└─────────────────────────────────────────────────────┘
```

```css
.page-footer {
  position: sticky;
  bottom: 0;
  z-index: 30;
  
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
  
  background: var(--surface-secondary);
  backdrop-filter: var(--glass-blur);
  border-top: 1px solid var(--glass-border);
  
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.sync-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.sync-indicator {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--status-active);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.pagination {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.pagination-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  
  background: var(--surface-primary);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.pagination-btn:hover:not(:disabled) {
  background: var(--surface-tertiary);
  border-color: var(--accent-conservative);
  color: var(--text-primary);
}

.pagination-btn.active {
  background: var(--accent-conservative);
  border-color: var(--accent-conservative);
  color: white;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

---

## ⚠️ AI Summary Warning

```css
.ai-warning-banner {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  margin: var(--space-4) 0;
  
  background: linear-gradient(135deg, 
    rgba(245, 158, 11, 0.1), 
    rgba(245, 158, 11, 0.05)
  );
  border-left: 4px solid var(--status-pending);
  border-radius: var(--radius-lg);
}

.ai-warning-icon {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  color: var(--status-pending);
}

.ai-warning-content {
  flex: 1;
}

.ai-warning-title {
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.ai-warning-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
}
```

**Warning Text:**
> ⚠️ **AI-Generated Summary**  
> This summary was generated by artificial intelligence and may contain inaccuracies. Always refer to the official bill text for authoritative information.

---

## 🎨 Creative Design Elements

### 1. Liquid Glass Background

```css
.liquid-glass-bg {
  position: fixed;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  pointer-events: none;
}

.liquid-glass-bg::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(
    circle at 50% 50%,
    rgba(37, 99, 235, 0.08) 0%,
    rgba(139, 92, 246, 0.05) 50%,
    transparent 100%
  );
  animation: rotate-gradient 30s linear infinite;
}

@keyframes rotate-gradient {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
```

### 2. Particle System (Subtle)

```typescript
// ParticleSystem.tsx
interface Particle {
  id: string;
  x: number;
  y: number;
  size: number;
  opacity: number;
  velocity: { x: number; y: number };
}

// Generate 20-30 particles floating across the viewport
// Use canvas or CSS animations for performance
```

### 3. Hover Glow Effect

```css
.glass-card {
  --glow-opacity: 0;
  transition: --glow-opacity 0.3s ease;
}

.glass-card:hover {
  --glow-opacity: 1;
}

.glass-card::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: var(--radius-xl);
  background: radial-gradient(
    600px circle at var(--mouse-x) var(--mouse-y),
    rgba(37, 99, 235, 0.15),
    transparent 40%
  );
  opacity: var(--glow-opacity);
  pointer-events: none;
  z-index: -1;
}
```

### 4. Status Timeline Component

```css
.status-timeline {
  position: relative;
  padding-left: var(--space-8);
}

.status-timeline::before {
  content: '';
  position: absolute;
  left: 12px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: linear-gradient(
    180deg,
    var(--status-active),
    var(--status-pending),
    var(--text-tertiary)
  );
}

.timeline-item {
  position: relative;
  padding: var(--space-3) 0;
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: -28px;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  border-radius: var(--radius-full);
  background: var(--surface-primary);
  border: 2px solid var(--status-active);
  box-shadow: 0 0 0 4px var(--surface-secondary);
}

.timeline-item.pending::before {
  border-color: var(--status-pending);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.timeline-item.upcoming::before {
  border-color: var(--text-tertiary);
  background: transparent;
}
```

---

## 📝 Design Checklist

### Pre-Launch Quality Gates

**Visual Design:**
- [ ] All colors meet WCAG AA contrast requirements
- [ ] Glass effect renders correctly across browsers
- [ ] Dark/light themes fully implemented
- [ ] All icons have proper ARIA labels
- [ ] Loading states designed for all components
- [ ] Empty states designed for all lists

**Responsive Design:**
- [ ] Mobile breakpoint (<768px) tested
- [ ] Tablet breakpoint (768-1279px) tested
- [ ] Desktop breakpoint (≥1280px) tested
- [ ] Touch targets ≥44x44px on mobile
- [ ] Horizontal scrolling prevented
- [ ] Viewport meta tag configured

**Performance:**
- [ ] Lighthouse score >90 (Performance)
- [ ] Lighthouse score >90 (Accessibility)
- [ ] Lighthouse score >90 (Best Practices)
- [ ] Images optimized (WebP, lazy loading)
- [ ] Fonts subset and preloaded
- [ ] Critical CSS inlined

**Accessibility:**
- [ ] Keyboard navigation functional
- [ ] Screen reader testing completed
- [ ] Focus indicators visible
- [ ] ARIA landmarks present
- [ ] Form labels properly associated
- [ ] Error messages announced

**Browser Compatibility:**
- [ ] Chrome/Edge (latest 2 versions)
- [ ] Firefox (latest 2 versions)
- [ ] Safari (latest 2 versions)
- [ ] Mobile Safari (iOS 15+)
- [ ] Chrome Mobile (Android 10+)

---

## 🔮 Future Enhancements

### Phase 2 Features
- Province/territory data integration
- Advanced search with natural language
- Personalized dashboards (save filters, watchlists)
- Email alerts for tracked bills/members
- Comparative analysis tools
- Data export (CSV, JSON, PDF)

### Phase 3 Features
- Interactive data visualizations (D3.js)
- Committee meeting video integration
- Member voting pattern analysis
- Bill impact assessment summaries
- Community discussion forums
- API access for developers

---

## 📞 Design System Governance

**Design Lead:** TBD  
**Frontend Lead:** TBD  
**Accessibility Lead:** TBD

**Review Cadence:**
- Weekly design review (Fridays 2pm)
- Monthly accessibility audit
- Quarterly design system update

**Contribution Guidelines:**
- All new components require design approval
- Accessibility checklist must be completed
- Performance impact must be measured
- Mobile responsiveness is mandatory

---

## 📚 References

**Design Inspiration:**
- [Glassmorphism by Michal Malewicz](https://hype4.academy/articles/design/glassmorphism-in-user-interfaces)
- [Liquid Design by Ramotion](https://www.ramotion.com/blog/liquid-design/)
- [Government Design Systems (UK, US, CA)](https://design-system.service.gov.uk/)

**Accessibility:**
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Inclusive Components by Heydon Pickering](https://inclusive-components.design/)

**Performance:**
- [Web Vitals by Google](https://web.dev/vitals/)
- [Next.js Performance Best Practices](https://nextjs.org/docs/basic-features/font-optimization)

---

**Document Version:** 1.0  
**Last Updated:** October 19, 2025  
**Status:** Ready for Implementation  
**Approval:** Pending