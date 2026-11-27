import { Alert, Button, Card, Spinner } from "react-bootstrap";

interface LoadingPanelProps {
  label?: string;
}

export function LoadingPanel({ label = "Загрузка..." }: LoadingPanelProps) {
  return (
    <div className="d-flex align-items-center justify-content-center py-5 gap-3">
      <Spinner animation="border" size="sm" />
      <span className="text-secondary">{label}</span>
    </div>
  );
}

interface ErrorPanelProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorPanel({ message, onRetry }: ErrorPanelProps) {
  return (
    <Card className="border-0 shadow-sm">
      <Card.Body>
        <Alert variant="danger" className="mb-0">
          <Alert.Heading>Ошибка запроса</Alert.Heading>
          <p className="mb-0">{message}</p>
          {onRetry && (
            <Button variant="outline-danger" size="sm" className="mt-3" onClick={onRetry}>
              Повторить
            </Button>
          )}
        </Alert>
      </Card.Body>
    </Card>
  );
}
