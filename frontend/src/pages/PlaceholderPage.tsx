interface PlaceholderPageProps {
  eyebrow: string;
  title: string;
  description: string;
}

export function PlaceholderPage({ eyebrow, title, description }: PlaceholderPageProps) {
  return (
    <section className="page-section">
      <div className="container narrow">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-copy">{description}</p>
        <div className="phase-notice">
          <strong>Foundation route ready.</strong>
          <span>Product behavior will be added in its planned implementation phase.</span>
        </div>
      </div>
    </section>
  );
}

