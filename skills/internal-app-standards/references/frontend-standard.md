# Frontend Standard

## Contents

- Required stack
- App structure
- Ant Design usage
- Layout and visual quality
- State and data fetching
- Forms, tables, and permissions

## Required Stack

- React.js + TypeScript.
- Vite for new projects.
- Ant Design as the component system.
- React Router for routing.
- TanStack Query or the existing repository standard for server state.
- Generated or shared typed API client when available.

## App Structure

Use feature-first structure inside `apps/web/src`:

```text
src/
├── app/                 # router, providers, global layout
├── features/
│   └── <feature>/
│       ├── api.ts
│       ├── hooks.ts
│       ├── pages/
│       ├── components/
│       └── types.ts
├── shared/
│   ├── components/
│   ├── constants/
│   ├── hooks/
│   └── utils/
├── styles/
└── main.tsx
```

## Ant Design Usage

- Use Ant Design primitives before custom components: `Layout`, `Menu`, `Breadcrumb`, `Table`, `Form`, `Modal`, `Drawer`, `Tabs`, `Segmented`, `Descriptions`, `Statistic`, `Alert`, `Tag`, `Tooltip`, `Empty`, `Skeleton`.
- Configure theme tokens centrally. Do not scatter one-off colors and spacing.
- Use `Form` validation rules for user-facing validation and backend validation for trust boundaries.
- Use `Table` with clear columns, pagination, sorting/filtering, empty state, and loading state.
- Use `Drawer` for side editing/detail workflows and `Modal` for short confirmations.

## Layout And Visual Quality

- Build the first screen as the actual internal tool, not a marketing landing page.
- Prefer dense, scannable operational layouts: filter bar, table/list, detail drawer, status tags, action buttons.
- Keep cards for repeated records or framed widgets. Do not nest cards inside cards.
- Avoid oversized hero sections, decorative gradients, stock-like illustrations, and demo placeholder copy.
- Use consistent spacing and stable component sizes so loading states and long text do not shift the layout.
- Ensure mobile and narrow desktop views do not overlap text, buttons, or table controls.
- Use clear empty, loading, error, disabled, and permission-denied states.

## State And Data Fetching

- Keep server state in query hooks; keep form state in Ant Design Form; keep global state minimal.
- Put API calls in feature-level `api.ts` or a shared API client, not directly in components.
- Handle request cancellation/retry behavior intentionally.
- Show actionable error messages and preserve user input when saves fail.

## Forms, Tables, And Permissions

- Forms must distinguish create, edit, read-only, and permission-denied states.
- Destructive actions require confirmation and visible result feedback.
- Table row actions should be icon or compact text actions with tooltips when needed.
- Do not hide authorization only in the frontend. Frontend checks are UX only; backend RBAC is mandatory.
