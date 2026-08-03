import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import ResearchLensPage from "./pages/ResearchLensPage";

export default function App() {
  return <Routes>
    <Route element={<Layout />}>
      <Route index element={<DashboardPage />} />
      <Route path="research/:sectionId" element={<ResearchLensPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Route>
  </Routes>;
}
