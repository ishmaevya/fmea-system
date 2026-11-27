import { Badge, Card, Col, Container, ListGroup, Row } from "react-bootstrap";
import { useAuth } from "../auth/AuthContext";
import { HealthBadge } from "../components/HealthBadge";

const roleLabels = {
  engineer: "Инженер-конструктор",
  quality: "Менеджер по качеству",
  admin: "Администратор",
} as const;

const backendFeatures = [
  "Каталог изделий, исполнений и компонентов",
  "Версионные FMEA-ревизии и workflow",
  "Пункты FMEA, RPN, приоритеты и фильтры",
  "Граф связей и массовое сохранение",
  "Вложения через MinIO",
  "LLM-заглушка с подтверждением инженером",
  "Отчёты и экспорт XLSX",
  "Журнал аудита для администратора",
];

const frontendSteps = [
  "Страницы входа и каталога",
  "Карточка изделия и список ревизий",
  "FMEA-таблица и массовое редактирование",
  "Граф зависимостей",
  "Подсказки, вложения и отчёты",
];

export function HomePage() {
  const { user } = useAuth();

  return (
    <Container>
      <Row className="g-4 align-items-stretch">
        <Col lg={7}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Body className="p-4">
              <div className="d-flex justify-content-between align-items-start mb-3">
                <div>
                  <h1 className="h3 mb-1">FMEA System</h1>
                  <p className="text-secondary mb-0">
                    Анализ видов и последствий отказов медицинских изделий
                  </p>
                </div>
                <HealthBadge />
              </div>

              {user && (
                <div className="mb-4">
                  <Badge bg="light" text="dark" className="me-2">
                    {user.email}
                  </Badge>
                  <Badge bg="primary">{roleLabels[user.role]}</Badge>
                </div>
              )}

              <p>
                Backend Этапа 3 готов и покрыт тестами. Сейчас строим frontend:
                навигацию, каталог, FMEA-таблицу, граф, вложения, подсказки и
                отчёты.
              </p>

              <h2 className="h6 text-uppercase text-secondary mt-4">
                Реализовано в backend
              </h2>
              <ListGroup variant="flush">
                {backendFeatures.map((feature) => (
                  <ListGroup.Item key={feature} className="px-0 bg-transparent">
                    {feature}
                  </ListGroup.Item>
                ))}
              </ListGroup>
            </Card.Body>
          </Card>
        </Col>

        <Col lg={5}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Body className="p-4">
              <h2 className="h5 mb-3">План frontend</h2>
              <ListGroup variant="flush" numbered>
                {frontendSteps.map((step) => (
                  <ListGroup.Item key={step} className="px-0 bg-transparent">
                    {step}
                  </ListGroup.Item>
                ))}
              </ListGroup>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
}
