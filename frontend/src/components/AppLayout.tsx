import { Breadcrumb, Container, Dropdown, Nav, Navbar } from "react-bootstrap";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { RoleGate } from "../auth/RoleGate";
import type { Role } from "../api/types";
import { HealthBadge } from "./HealthBadge";

const roleLabels: Record<Role, string> = {
  engineer: "Инженер-конструктор",
  quality: "Менеджер по качеству",
  admin: "Администратор",
};

const routeLabels: Record<string, string> = {
  "/": "Главная",
  "/login": "Вход",
};

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const currentLabel =
    routeLabels[location.pathname] ??
    location.pathname.split("/").filter(Boolean).join(" / ");

  return (
    <div className="min-vh-100 d-flex flex-column">
      <Navbar bg="dark" data-bs-theme="dark" expand="lg">
        <Container fluid>
          <Navbar.Brand as={Link} to="/">
            FMEA System
          </Navbar.Brand>
          <Navbar.Toggle aria-controls="main-nav" />
          <Navbar.Collapse id="main-nav">
            <Nav className="me-auto">
              <Nav.Link as={Link} to="/">
                Главная
              </Nav.Link>
              <Nav.Link disabled>Изделия</Nav.Link>
              <Nav.Link disabled>Ревизии</Nav.Link>
              <Nav.Link disabled>Отчёты</Nav.Link>
              <RoleGate roles={["admin"]}>
                <Nav.Link disabled>Аудит</Nav.Link>
              </RoleGate>
            </Nav>
            <div className="d-flex align-items-center gap-3">
              <HealthBadge />
              {user && (
                <Dropdown align="end">
                  <Dropdown.Toggle variant="outline-light" size="sm" id="user-menu">
                    {user.email} · {roleLabels[user.role]}
                  </Dropdown.Toggle>
                  <Dropdown.Menu>
                    <Dropdown.ItemText>
                      {user.position || "Должность не указана"}
                    </Dropdown.ItemText>
                    <Dropdown.Divider />
                    <Dropdown.Item onClick={handleLogout}>Выйти</Dropdown.Item>
                  </Dropdown.Menu>
                </Dropdown>
              )}
            </div>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      <Container fluid className="py-4 flex-grow-1">
        <Breadcrumb className="mb-4">
          <Breadcrumb.Item linkAs={Link} linkProps={{ to: "/" }}>
            Главная
          </Breadcrumb.Item>
          {location.pathname !== "/" && (
            <Breadcrumb.Item active>{currentLabel}</Breadcrumb.Item>
          )}
        </Breadcrumb>
        <Outlet />
      </Container>
    </div>
  );
}
