import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ToastProvider } from './design/primitives';
import { AppShell } from './app/AppShell';
const LandingPage=lazy(() => import('./features/upload/LandingPage').then(m => ({default:m.LandingPage})));
const WorkspaceRouter=lazy(() => import('./app/WorkspaceRouter').then(m => ({default:m.WorkspaceRouter})));
import { NotFoundPage } from './app/NotFoundPage';
const KitPage=lazy(() => import('./design/KitPage').then(m => ({default:m.KitPage})));
const PrivacyCheckPage=lazy(() => import('./features/privacy/PrivacyCheckPage').then(m => ({default:m.PrivacyCheckPage})));

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <AppShell>
          <Suspense fallback={<div role="status" className="p-8 text-center">Loading workspace…</div>}><Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/workspace" element={<WorkspaceRouter />} />
            <Route path="/privacy-check" element={<PrivacyCheckPage />} />
            {import.meta.env.DEV && <Route path="/kit" element={<KitPage />} />}
            <Route path="*" element={<NotFoundPage />} />
          </Routes></Suspense>
        </AppShell>
      </BrowserRouter>
    </ToastProvider>
  );
}
