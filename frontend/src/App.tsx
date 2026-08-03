import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ResearchLensPage from "./pages/ResearchLensPage";

export default function App() {
  return <Routes>
    <Route element={<Layout />}>
      <Route index element={<Navigate to="/research/capex-transmission" replace />} />
      <Route path="research/:sectionId" element={<ResearchLensPage />} />
      <Route path="*" element={<Navigate to="/research/capex-transmission" replace />} />
    </Route>
  </Routes>;
}
