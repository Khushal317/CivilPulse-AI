import { createBrowserRouter, type RouteObject } from "react-router-dom";

import { AdminLayout } from "../layouts/AdminLayout";
import { AdminDashboardPage } from "../features/admin/AdminDashboardPage";
import { AdminIssueDetailPage } from "../features/admin/AdminIssueDetailPage";
import { AdminIssuesPage } from "../features/admin/AdminIssuesPage";
import { AdminLoginPage } from "../features/admin/AdminLoginPage";
import { AdminMissionsPage } from "../features/admin/AdminMissionsPage";
import { AreaDetailPage } from "../features/areas/AreaDetailPage";
import { NeighborhoodArenaPage } from "../features/areas/NeighborhoodArenaPage";
import { RankingsPage } from "../features/areas/RankingsPage";
import { IssueDetailPage } from "../features/issues/IssueDetailPage";
import { TrackerPage } from "../features/issues/TrackerPage";
import { MissionDetailPage } from "../features/missions/MissionDetailPage";
import { MissionsPage } from "../features/missions/MissionsPage";
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
      {
        path: "neighborhoods",
        element: <NeighborhoodArenaPage />,
      },
      {
        path: "neighborhoods/:slug",
        element: <AreaDetailPage />,
      },
      {
        path: "rankings",
        element: <RankingsPage />,
      },
      {
        path: "missions",
        element: <MissionsPage />,
      },
      {
        path: "missions/:missionId",
        element: <MissionDetailPage />,
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
      {
        path: "missions",
        element: <AdminMissionsPage />,
      },
    ],
  },
];

export const router = createBrowserRouter(appRoutes);
