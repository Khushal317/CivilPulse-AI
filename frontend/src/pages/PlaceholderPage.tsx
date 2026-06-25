import type { ReactNode } from "react";

import { Card } from "../components/ui/Card";

interface PlaceholderPageProps {
  children?: ReactNode;
  eyebrow: string;
  title: string;
  description: string;
}

export function PlaceholderPage({
  children,
  eyebrow,
  title,
  description,
}: PlaceholderPageProps) {
  return (
    <section className="page-section">
      <div className="container narrow">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-copy">{description}</p>
        <Card className="phase-notice">
          <strong>Foundation route ready.</strong>
          <span>Product behavior will be added in its planned implementation phase.</span>
        </Card>
        {children}
      </div>
    </section>
  );
}
