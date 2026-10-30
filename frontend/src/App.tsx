import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ToastProvider } from './design/primitives';
import { AppShell } from './app/AppShell';
import { LandingPage } from './features/upload/LandingPage';
import { WorkspaceRouter } from './app/WorkspaceRouter';
import { NotFoundPage } from './app/NotFoundPage';
import { KitPage } from './design/KitPage';
import { PrivacyCheckPage } from './features/privacy/PrivacyCheckPage';

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <AppShell>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/workspace" element={<WorkspaceRouter />} />
            <Route path="/privacy-check" element={<PrivacyCheckPage />} />
            {import.meta.env.DEV && <Route path="/kit" element={<KitPage />} />}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AppShell>
      </BrowserRouter>
    </ToastProvider>
  );
}
