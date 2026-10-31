import React from 'react';

interface PrivacyCubeProps {
  className?: string;
}

export const PrivacyCube: React.FC<PrivacyCubeProps> = ({ className = '' }) => {
  return (
    <div className={`cubewrap ${className}`} aria-hidden="true">
      <div className="cube">
        <div>
          <span>
            <b>🔒</b>Temporary processing
          </span>
        </div>
        <div>
          <span>
            <b>🗑</b>Delete session
          </span>
        </div>
        <div>
          <span>
            <b>🚫</b>No storage
          </span>
        </div>
        <div>
          <span>
            <b>📖</b>Information only
          </span>
        </div>
      </div>
    </div>
  );
};

export default PrivacyCube;
