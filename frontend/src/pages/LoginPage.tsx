import { useState, type FormEvent } from "react";
import { Alert, Button, Card, Col, Container, Form, Row, Spinner } from "react-bootstrap";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { getErrorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { login, user, initializing } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const from = (location.state as { from?: string } | null)?.from ?? "/";

  if (initializing) {
    return (
      <Container className="py-5 text-center">
        <Spinner animation="border" role="status" />
      </Container>
    );
  }

  if (user) {
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (cause) {
      setError(getErrorMessage(cause));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container className="py-5">
      <Row className="justify-content-center">
        <Col xs={12} md={8} lg={5}>
          <Card className="border-0 shadow-sm">
            <Card.Body className="p-4">
              <h1 className="h3 mb-1">Вход в FMEA System</h1>
              <p className="text-secondary mb-4">
                Введите email и пароль для доступа к workspace.
              </p>

              {error && <Alert variant="danger">{error}</Alert>}

              <Form onSubmit={handleSubmit}>
                <Form.Group className="mb-3" controlId="login-email">
                  <Form.Label>Email</Form.Label>
                  <Form.Control
                    type="email"
                    autoComplete="username"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="engineer@example.com"
                    required
                  />
                </Form.Group>

                <Form.Group className="mb-4" controlId="login-password">
                  <Form.Label>Пароль</Form.Label>
                  <Form.Control
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                  />
                </Form.Group>

                <Button type="submit" variant="primary" disabled={submitting}>
                  {submitting ? "Вход..." : "Войти"}
                </Button>
              </Form>

              <div className="mt-4 small text-secondary">
                Демо: <code>engineer@example.com</code> /{" "}
                <code>Pass12345!</code>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
}
