import React from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';
import Navbar from './components/Navbar';
import PdfConverter from './components/PdfConverter';

function App() {
  return (
    <div className="app">
      <Navbar />
      <PdfConverter />
    </div>
  );
}

export default App; 