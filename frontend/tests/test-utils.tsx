import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import type { ReactElement } from "react";

import { NotificationProvider } from "../src/app/notifications";

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export function renderWithProviders(
  element: ReactElement,
  {
    route = "/",
    ...options
  }: RenderOptions & { route?: string } = {},
) {
  const queryClient = createTestQueryClient();
  const router = createMemoryRouter([{ path: "*", element }], {
    initialEntries: [route],
  });

  return {
    queryClient,
    router,
    ...render(
      <QueryClientProvider client={queryClient}>
        <NotificationProvider>
          <RouterProvider router={router} />
        </NotificationProvider>
      </QueryClientProvider>,
      options,
    ),
  };
}

