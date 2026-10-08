import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { queryClient } from './lib/api/queryClient';
import { ErrorBoundary } from '@xian/ui';
import { App } from './App';
import '@xian/ui/styles/tokens.css';
import './styles/globals.css';
import './styles/animations.css';

const container = document.getElementById('root');
if (!container) throw new Error('root container missing');

ReactDOM.createRoot(container).render(
  <React.StrictMode>
    <ErrorBoundary label="应用启动异常">
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>
);