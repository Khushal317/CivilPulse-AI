import type { ReactNode } from "react";

export interface TimelineItem {
  id: string;
  title: string;
  description?: ReactNode;
  meta?: string;
  state?: "complete" | "current" | "upcoming";
}

export function Timeline({ items, label = "Issue progress" }: { items: TimelineItem[]; label?: string }) {
  return (
    <ol className="timeline" aria-label={label}>
      {items.map((item) => (
        <li className={`timeline-item timeline-${item.state ?? "upcoming"}`} key={item.id}>
          <span className="timeline-marker" aria-hidden="true" />
          <div>
            <div className="timeline-heading">
              <strong>{item.title}</strong>
              {item.meta && <span>{item.meta}</span>}
            </div>
            {item.description && <div className="timeline-description">{item.description}</div>}
          </div>
        </li>
      ))}
    </ol>
  );
}

