# Frontend Architecture

## Structure

```text
src/
├── api/          # HTTP client and endpoint functions
├── app/          # Global providers, notifications, and error boundaries
├── components/
│   ├── feedback/ # Loading, empty, and error states
│   ├── navigation/
│   └── ui/       # Reusable accessible primitives
├── features/     # Product behavior grouped by feature in later phases
├── layouts/      # Public and admin application shells
├── pages/        # Route-level composition
├── routes/       # Route tree
├── styles/       # Tokens, global rules, components, layouts, and pages
├── types/        # Shared frontend domain types
└── utils/        # Framework-independent helpers
```

## Component Rules

- Keep domain workflows inside `features`; do not place business logic in generic UI components.
- Promote a component to `components/ui` only when it is reusable and product-neutral.
- Every form control owns a visible label and programmatic hint/error association.
- Buttons use real `<button>` elements; navigation uses links.
- Dialogs move focus inside, trap keyboard focus, close with Escape, and restore the previous focus.
- Loading, empty, and failure states are designed components rather than ad hoc text.
- Status, severity, and category colors always include readable text labels.

## State and Data

- TanStack Query owns server state.
- Local component state owns temporary UI state.
- The typed API client normalizes credentials, JSON bodies, backend error envelopes, and request identifiers.
- API functions return domain-specific response types and stay separate from page components.
- Notifications are global but invoked through a small context API.

## Styling

- Design decisions are expressed as CSS custom-property tokens.
- Component styles do not use hard-coded brand colors when a semantic token exists.
- Layout breakpoints start from narrow screens and preserve 44-pixel minimum interactive targets.
- Reduced-motion preferences disable nonessential animation.
- Public and admin layouts remain separate so either can evolve without coupling navigation structures.

## Testing

- Shared test utilities provide query and notification providers.
- Component tests cover accessible names, keyboard interactions, focus behavior, and state feedback.
- `jest-axe` provides a reusable automated accessibility check.
- Route-shell tests verify each primary path renders in its intended public or admin layout.
- Browser verification covers desktop and mobile widths and checks for horizontal overflow.
