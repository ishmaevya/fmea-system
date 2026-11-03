import { Card, Col, Container, ListGroup, Row } from "react-bootstrap";
import { HealthBadge } from "../components/HealthBadge";

const nextSteps = [
  "Модели изделия, компонентов и FMEA-ревизий",
  "JWT-авторизация и разграничение ролей",
  "FMEA-таблица с расчётом RPN",
  "Граф зависимостей отказов",
  "Отчёты и экспорт",
  "LLM-подсказки",
];

export function HomePage() {
  return (
    <Container className="py-5">
      <Row className="g-4 align-items-stretch">
        <Col lg={7}>
          <Card className="h-100 shadow-sm border-0">
            <Card.Body className="p-4">
              <div className="d-flex justify-content-between align-items-start mb-3">
                <div>
                  <h1 className="h3 mb-1">FMEA System</h1>
                  <p className="text-secondary mb-0">
                    Каркас проекта готов к разработке доменной модели.
                  </p>
                </div>
                <HealthBadge />
              </div>
              <p className="mb-3">
                Система предназначена для ведения анализа видов и последствий
                отказов медицинских изделий: структура изделия, ревизии FMEA,
                оценки риска, связи между отказами и отчёты.
              </p>
              <Card className="bg-light border-0">
                <Card.Body>
                  <h2 className="h6 text-uppercase text-secondary">
                    Реализовано на шаге 2
                  </h2>
                  <ListGroup variant="flush">
                    <ListGroup.Item className="bg-transparent px-0">
                      Django 5 + DRF + SimpleJWT, кастомный пользователь
                    </ListGroup.Item>
                    <ListGroup.Item className="bg-transparent px-0">
                      PostgreSQL, Redis и MinIO в docker-compose
                    </ListGroup.Item>
                    <ListGroup.Item className="bg-transparent px-0">
                      Health-check и Swagger-документация API
                    </ListGroup.Item>
                  </ListGroup>
                </Card.Body>
              </Card>
            </Card.Body>
          </Card>
        </Col>
        <Col lg={5}>
          <Card className="h-100 shadow-sm border-0">
            <Card.Body className="p-4">
              <h2 className="h5 mb-3">Следующие шаги</h2>
              <ListGroup variant="flush">
                {nextSteps.map((step) => (
                  <ListGroup.Item key={step} className="bg-transparent px-0">
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
