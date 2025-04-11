import React, { useState } from 'react';
// Removed Row, Col from react-bootstrap import
import { Card, Button, Alert, Spinner } from 'react-bootstrap'; 
import { useDropzone } from 'react-dropzone';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faCloudUploadAlt, 
  faFolderOpen, 
  faFilePdf, 
  faCog, 
  faCheckCircle, 
  faExclamationCircle,
  faFileAlt,
  faList
} from '@fortawesome/free-solid-svg-icons';
import axios from 'axios';
import MarkdownPreview from './MarkdownPreview';

const PdfConverter = () => {
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [statusType, setStatusType] = useState('');
  const [convertedFiles, setConvertedFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [showUpload, setShowUpload] = useState(true); // Control visibility of upload section

  const onDrop = (acceptedFiles) => {
    const pdfFiles = acceptedFiles.filter(file => 
      file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
    );
    setFiles(pdfFiles);
    setStatusMessage(null); // Clear status on new drop
    setConvertedFiles([]); // Clear previous results
    setSelectedFile(null);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    }
  });

  const handleSubmit = async (event) => {
    if (event) event.preventDefault();
    
    if (files.length === 0) {
      setStatusMessage('Please select at least one PDF file.');
      setStatusType('warning');
      return;
    }

    setIsProcessing(true);
    setStatusMessage(null);
    setConvertedFiles([]);
    setSelectedFile(null);
    
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files[]', file);
    });

    try {
      const response = await axios.post('/convert', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      const data = response.data;

      if (data.success) {
        setStatusMessage('Conversion successful! Files are ready below.');
        setStatusType('success');
        setConvertedFiles(data.files);
        setFiles([]); // Clear selected files after successful conversion
        setShowUpload(false); // Hide upload section
        // Select the first converted file by default
        if (data.files.length > 0) {
          setSelectedFile(data.files[0]);
        }
      } else {
        setStatusMessage(`Error: ${data.message || 'Conversion failed.'}`);
        setStatusType('danger');
      }
    } catch (error) {
      console.error('Error:', error);
      setStatusMessage(`Network error or server unavailable: ${error.message}`);
      setStatusType('danger');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleStartNewConversion = () => {
    setFiles([]);
    setConvertedFiles([]);
    setSelectedFile(null);
    setStatusMessage(null);
    setShowUpload(true); // Show upload section again
  };

  const dropzoneClassName = `upload-zone ${isDragActive ? 'dragover' : ''}`;

  return (
    // Replaced Row with div
    <div className="main-layout-row"> 
      {/* Replaced Col with div */}
      <div className="sidebar-col"> 
        <div className="sidebar-content">
          <h4 className="sidebar-title">
            <FontAwesomeIcon icon={faList} className="me-2" />
            Converted Files
          </h4>
          {convertedFiles.length > 0 ? (
            <ul className="results-list">
              {convertedFiles.map((file, index) => (
                <li 
                  key={index}
                  className={selectedFile?.url === file.url ? 'active' : ''}
                  onClick={() => setSelectedFile(file)}
                >
                  <FontAwesomeIcon icon={faFileAlt} className="me-3 flex-shrink-0" />
                  <span className="file-name-truncate">{file.name}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-muted text-center p-3 small">
              No files converted yet.
            </div>
          )}
          <Button 
            variant="outline-secondary" 
            size="sm" 
            className="mt-3 w-100" 
            onClick={handleStartNewConversion}
          >
            Start New Conversion
          </Button>
        </div>
      </div> {/* End sidebar-col div */}

      {/* Replaced Col with div */}
      <div className="main-content-col"> 
        {showUpload ? (
          <Card className="mb-4 upload-card">
            <Card.Body>
              <form onSubmit={handleSubmit}>
                <div {...getRootProps({ className: dropzoneClassName })}>
                  <input {...getInputProps()} />
                  <FontAwesomeIcon icon={faCloudUploadAlt} className="upload-icon" />
                  <h3 className="mb-3">Drop your PDF files here</h3>
                  <p className="text-muted mb-3">or</p>
                  <Button 
                    variant="primary" 
                    onClick={(e) => {
                      e.stopPropagation();
                      document.querySelector('input[type="file"]').click();
                    }}
                  >
                    <FontAwesomeIcon icon={faFolderOpen} className="me-2" />
                    Browse Files
                  </Button>
                  
                  {files.length > 0 && (
                    <div className="selected-files">
                      <h6 className="mb-2">Selected Files:</h6>
                      <div>
                        {files.map((file, index) => (
                          <div key={index} className="file-item">
                            <FontAwesomeIcon icon={faFilePdf} className="file-icon flex-shrink-0" />
                            <span className="file-name-truncate">{file.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="text-center mt-4">
                  <Button 
                    type="submit" 
                    variant="primary" 
                    size="lg" 
                    disabled={isProcessing || files.length === 0}
                  >
                    {isProcessing ? (
                      <span className="processing-indicator">
                        <Spinner animation="border" size="sm" />
                        Processing...
                      </span>
                    ) : (
                      <>
                        <FontAwesomeIcon icon={faCog} className="me-2" />
                        Convert Files
                      </>
                    )}
                  </Button>
                </div>
                
                {statusMessage && (
                  <div className="mt-4">
                    <Alert variant={statusType}>
                      <FontAwesomeIcon 
                        icon={statusType === 'success' ? faCheckCircle : faExclamationCircle} 
                        className="me-2" 
                      />
                      {statusMessage}
                    </Alert>
                  </div>
                )}
              </form>
            </Card.Body>
          </Card>
        ) : (
          selectedFile ? (
            <MarkdownPreview file={selectedFile} />
          ) : (
            <div className="text-center text-muted p-5">
              <FontAwesomeIcon icon={faFileAlt} className="fa-3x mb-3" />
              <p>Select a file from the list to preview its content</p>
            </div>
          )
        )}
      </div> {/* End main-content-col div */}
    </div> // End main-layout-row div
  );
};

export default PdfConverter;
