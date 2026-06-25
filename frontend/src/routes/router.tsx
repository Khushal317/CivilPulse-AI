import { createBrowserRouter, type RouteObject } from "react-router-dom";

import { AdminLayout } from "../layouts/AdminLayout";
import { ReportPage } from "../features/reports/ReportPage";
import { ReportReviewPage } from "../features/reports/ReportReviewPage";
import { PublicLayout } from "../layouts/PublicLayout";
import { HomePage } from "../pages/HomePage";
import { PlaceholderPage } from "../pages/PlaceholderPage";
import { RouteErrorPage } from "../pages/RouteErrorPage";

export const appRoutes: RouteObject[] = [
  {
    element: <PublicLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <HomePage /> },
      {
        path: "report",
        element: <ReportPage />,
      },
      {
        path: "report/review/:draftId",
        element: <ReportReviewPage />,
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
      { path: "*", element: <RouteErrorPage /> },
    ],
  },
  {
    path: "/admin",
    element: <AdminLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      {
        index: true,
        element: (
          <PlaceholderPage
            eyebrow="Issue management"
            title="Administrator dashboard"
            description="Dashboard metrics and secure management tools will be implemented in Phase 7."
          />
        ),
      },
      {
        path: "issues",
        element: (
          <PlaceholderPage
            eyebrow="Admin issue queue"
            title="Manage reported issues"
            description="Filtering, status updates, and public notes will be implemented in Phase 7."
          />
        ),
      },
    ],
  },
];

export const router = createBrowserRouter(appRoutes);
