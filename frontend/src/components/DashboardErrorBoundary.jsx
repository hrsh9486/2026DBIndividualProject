import { Component } from "react";
import { ErrorBlock } from "./DataState";

export default class DashboardErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("Dashboard render error:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <ErrorBlock
          message={`${this.state.error.message} — likely a mismatch between the JSON shape this component expects and what the file actually contains. Check the browser console for the full stack.`}
        />
      );
    }
    return this.props.children;
  }
}
