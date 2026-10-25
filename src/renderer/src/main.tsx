import React from 'react'
import ReactDOM from 'react-dom/client'
import './mock' // installs a window.aplica mock only if the Electron preload is absent
import App from './App'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
