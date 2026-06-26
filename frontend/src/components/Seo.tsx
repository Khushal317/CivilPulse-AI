import { useEffect } from "react";

const PRODUCT_NAME = "CivicPulse AI";

interface SeoProps {
  title?: string;
  description?: string;
}

export function Seo({ title, description }: SeoProps) {
  useEffect(() => {
    document.title = title ? `${title} · ${PRODUCT_NAME}` : PRODUCT_NAME;

    if (description) {
      const meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
      meta?.setAttribute("content", description);
    }
  }, [description, title]);

  return null;
}
