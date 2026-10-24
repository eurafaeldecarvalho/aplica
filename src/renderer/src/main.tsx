import React from 'react'
import ReactDOM from 'react-dom/client'
import './mock' // instala um mock de window.aplica só se o preload do Electron não existir
import App from './App'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
