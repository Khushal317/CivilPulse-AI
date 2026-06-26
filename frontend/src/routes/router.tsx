import { createBrowserRouter, type RouteObject } from "react-router-dom";

import { AdminLayout } from "../layouts/AdminLayout";
import { AdminDashboardPage } from "../features/admin/AdminDashboardPage";
import { AdminIssueDetailPage } from "../features/admin/AdminIssueDetailPage";
import { AdminIssuesPage } from "../features/admin/AdminIssuesPage";
import { AdminLoginPage } from "../features/admin/AdminLoginPage";
import { IssueDetailPage } from "../features/issues/IssueDetailPage";
import { TrackerPage } from "../features/issues/TrackerPage";
import { ReportPage } from "../features/reports/ReportPage";
import { ReportReviewPage } from "../features/reports/ReportReviewPage";
import { PublicLayout } from "../layouts/PublicLayout";
import { HomePage } from "../pages/HomePage";
import { NotFoundPage } from "../pages/NotFoundPage";
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
        element: <TrackerPage />,
      },
      {
        path: "issues/:issueId",
        element: <IssueDetailPage />,
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  {
    path: "/admin/login",
    element: <AdminLoginPage />,
    errorElement: <RouteErrorPage />,
  },
  {
    path: "/admin",
    element: <AdminLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      {
        index: true,
        element: <AdminDashboardPage />,
      },
      {
        path: "issues",
        element: <AdminIssuesPage />,
      },
      {
        path: "issues/:issueId",
        element: <AdminIssueDetailPage />,
      },
    ],
  },
];

export const router = createBrowserRouter(appRoutes);
