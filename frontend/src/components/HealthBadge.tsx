import { useEffect, useState } from "react";
import { Badge, Spinner } from "react-bootstrap";
import { fetchHealth, type HealthResponse } from "../api/health";

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; data: HealthResponse }
  | { kind: "error"; message: string };

export function HealthBadge() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then((data) => {
        if (!cancelled) {
          setState({ kind: "ok", data });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message: error instanceof Error ? error.message : "Неизвестная ошибка",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind === "loading") {
    return (
      <Badge bg="secondary">
        <Spinner animation="border" size="sm" className="me-2" />
        Проверка API
      </Badge>
    );
  }

  if (state.kind === "error") {
    return <Badge bg="danger">API недоступен</Badge>;
  }

  return (
    <Badge bg={state.data.status === "ok" ? "success" : "warning"}>
      API: {state.data.status} · v{state.data.version}
    </Badge>
  );
}
