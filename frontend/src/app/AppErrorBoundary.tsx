import { Component, type ErrorInfo, type ReactNode } from "react";

import { ErrorState } from "../components/feedback/ErrorState";

interface AppErrorBoundaryProps {
  children: ReactNode;
}

interface AppErrorBoundaryState {
  hasError: boolean;
}

export class AppErrorBoundary extends Component<
  AppErrorBoundaryProps,
  AppErrorBoundaryState
> {
  state: AppErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): AppErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Uncaught application error", error, info.componentStack);
  }

  private reset = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <main className="page-section">
          <div className="container narrow">
            <ErrorState
              description="The page encountered an unexpected problem. Try restoring the application."
              onRetry={this.reset}
              title="The application needs a reset"
            />
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}

