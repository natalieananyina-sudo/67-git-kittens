import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import BloodBackground from "./components/BloodBackground";
import BatchPage from "./pages/BatchPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import SinglePage from "./pages/SinglePage";

export default function App() {
  // Фон один на всё приложение: при входе он не перезапускается, а плавно «стихает»
  const { pathname } = useLocation();

  return (
    <>
      <BloodBackground mode={pathname === "/" ? "login" : "workspace"} />
      <Routes>
        {/* Вход врача */}
        <Route path="/" element={<LoginPage />} />

        {/* Рабочая область (только после входа) */}
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="single" element={<SinglePage />} />
          <Route path="batch" element={<BatchPage />} />
        </Route>

        {/* Любой неизвестный адрес ведёт на экран входа */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
