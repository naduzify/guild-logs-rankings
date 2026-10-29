import { Component, StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';

// A rendering error (odd link, unexpected data) shows a way back instead of a blank page.
class Fallback extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="wrap">
        <p className="empty">Something went wrong on this page. <a href="#/" onClick={() => this.setState({ error: null })}>Back to the guild page</a>.</p>
      </main>
    );
  }
}

// Coming from the guild chooser's transition (chooser.js): the content fades in on the guild's colour.
try {
  if (sessionStorage.getItem('clt:enter')) {
    sessionStorage.removeItem('clt:enter');
    document.body.classList.add('enter');
  }
} catch { /* storage blocked: no fade-in */ }

createRoot(document.getElementById('root')).render(<StrictMode><Fallback><App /></Fallback></StrictMode>);
