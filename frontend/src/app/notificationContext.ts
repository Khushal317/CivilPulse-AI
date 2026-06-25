import { createContext, useContext } from "react";

export type NotificationTone = "success" | "info" | "error";

export interface NotificationInput {
  message: string;
  title: string;
  tone?: NotificationTone;
}

export interface NotificationContextValue {
  notify: (notification: NotificationInput) => void;
}

export const NotificationContext = createContext<NotificationContextValue | null>(null);

export function useNotifications(): NotificationContextValue {
  const context = useContext(NotificationContext);
  if (context === null) {
    throw new Error("useNotifications must be used within NotificationProvider");
  }
  return context;
}

