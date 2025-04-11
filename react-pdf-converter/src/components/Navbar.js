import React from 'react';
import { Navbar as BootstrapNavbar, Container } from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faFileAlt } from '@fortawesome/free-solid-svg-icons';

const Navbar = () => {
  return (
    <BootstrapNavbar bg="white" className="shadow-sm">
      <Container>
        <BootstrapNavbar.Brand href="#" className="fw-bold" style={{ color: 'var(--primary-color)' }}>
          <FontAwesomeIcon icon={faFileAlt} className="me-2" />
          PDF to Markdown
        </BootstrapNavbar.Brand>
      </Container>
    </BootstrapNavbar>
  );
};

export default Navbar; 