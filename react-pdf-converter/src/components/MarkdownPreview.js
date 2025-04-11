import React, { useState, useEffect } from 'react';
import { Button, Spinner, Alert, Row, Col } from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faDownload, faFileAlt, faExclamationTriangle, faEdit } from '@fortawesome/free-solid-svg-icons'; // Removed faEye
import MDEditor from '@uiw/react-md-editor';
import axios from 'axios';

const MarkdownPreview = ({ file }) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchContent = async () => {
      if (!file) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const response = await axios.get(`http://localhost:5000${file.url}`, {
          headers: {
            'Accept': 'text/markdown, text/plain, */*'
          }
        });
        
        if (typeof response.data === 'string') {
          setContent(response.data);
        } else {
          throw new Error('Invalid response format');
        }
      } catch (err) {
        console.error('Error fetching markdown:', err);
        setError(
          err.response?.data?.error || 
          err.message || 
          'Failed to load markdown content'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchContent();
  }, [file]);

  const handleDownload = () => {
    window.open(`http://localhost:5000${file.url}`, '_blank');
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center h-100">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Loading...</span>
        </Spinner>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="danger" className="m-3">
        <div className="d-flex align-items-center">
          <FontAwesomeIcon icon={faExclamationTriangle} className="me-2" size="lg" />
          <div>
            <h6 className="mb-1">Error Loading Content</h6>
            <p className="mb-0">{error}</p>
          </div>
        </div>
      </Alert>
    );
  }

  return (
    <div className="markdown-preview">
      <div className="preview-header">
        <div className="d-flex align-items-center">
          <FontAwesomeIcon icon={faFileAlt} className="me-2" />
          <h4>{file.name}</h4>
        </div>
        <Button variant="primary" size="sm" onClick={handleDownload}>
          <FontAwesomeIcon icon={faDownload} className="me-2" />
          Download
        </Button>
      </div>
      {/* Removed Row and Col wrappers, pane-header and editor-container are now direct children */}
      <div className="pane-header">
        <FontAwesomeIcon icon={faEdit} className="me-2" />
        Editor
          </div>
          <div className="editor-container">
            <MDEditor
              value={content}
              onChange={setContent}
              preview="edit"
              hideToolbar={false}
              enableScroll={true}
            />
      </div> {/* End of editor-container */}
    </div> /* End of markdown-preview */
  );
};

export default MarkdownPreview;
