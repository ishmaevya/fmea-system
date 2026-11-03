import { Container, Navbar } from "react-bootstrap";
import { HomePage } from "./pages/HomePage";

export default function App() {
  return (
    <>
      <Navbar bg="dark" data-bs-theme="dark" expand="lg">
        <Container>
          <Navbar.Brand href="/">FMEA System</Navbar.Brand>
          <Navbar.Text className="text-light-emphasis">
            Анализ видов и последствий отказов
          </Navbar.Text>
        </Container>
      </Navbar>
      <HomePage />
    </>
  );
}
