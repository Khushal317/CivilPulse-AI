import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "../layouts/AppLayout";
import { HomePage } from "../pages/HomePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { PlaceholderPage } from "../pages/PlaceholderPage";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      {
        path: "report",
        element: (
          <PlaceholderPage
            eyebrow="Citizen reporting"
            title="Report a local issue"
            description="The AI-assisted reporting and review flow will be implemented in Phase 4."
          />
        ),
      },
      {
        path: "issues",
        element: (
          <PlaceholderPage
            eyebrow="Public transparency"
            title="Public issue tracker"
            description="Filtering, search, issue cards, and pagination will be implemented in Phase 5."
          />
        ),
      },
      {
        path: "admin",
        element: (
          <PlaceholderPage
            eyebrow="Issue management"
            title="Administrator dashboard"
            description="Secure authentication and issue management will be implemented in Phase 7."
          />
        ),
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

