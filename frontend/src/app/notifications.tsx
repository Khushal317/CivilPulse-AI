import { useCallback, useMemo, useState, type PropsWithChildren } from "react";

import { Button } from "../components/ui/Button";
import {
  NotificationContext,
  type NotificationInput,
  type NotificationTone,
} from "./notificationContext";

interface Notification {
  id: number;
  message: string;
  title: string;
  tone: NotificationTone;
}

export function NotificationProvider({ children }: PropsWithChildren) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const dismiss = useCallback((id: number) => {
    setNotifications((current) => current.filter((notification) => notification.id !== id));
  }, []);

  const notify = useCallback((input: NotificationInput) => {
    const id = Date.now() + Math.random();
    setNotifications((current) => [
      ...current,
      { ...input, id, tone: input.tone ?? "info" },
    ]);
    window.setTimeout(() => {
      setNotifications((current) => current.filter((notification) => notification.id !== id));
    }, 5_000);
  }, []);

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <div className="notification-region" aria-label="Notifications">
        {notifications.map((notification) => (
          <div
            className={`notification notification-${notification.tone}`}
            key={notification.id}
            role={notification.tone === "error" ? "alert" : "status"}
          >
            <div>
              <strong>{notification.title}</strong>
              <p>{notification.message}</p>
            </div>
            <Button
              aria-label={`Dismiss ${notification.title}`}
              onClick={() => dismiss(notification.id)}
              size="small"
              variant="ghost"
            >
              ×
            </Button>
          </div>
        ))}
      </div>
    </NotificationContext.Provider>
  );
}
