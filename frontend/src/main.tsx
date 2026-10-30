import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './design/tokens.css';
import { I18nProvider } from './lib/i18n';
import { SessionProvider } from './lib/session';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <I18nProvider>
      <SessionProvider>
        <App />
      </SessionProvider>
    </I18nProvider>
  </React.StrictMode>
);
