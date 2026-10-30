/**
 * PrivacyCube Component
 * Exact match to the preview HTML:
 * - 3D spinning frosted glass cube (.cube)
 * - 4 distinct perspective faces with emojis and promises
 * - CSS transform-style: preserve-3d with 16s continuous rotation
 */

import React from 'react';

export const PrivacyCube: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div className={`cubewrap select-none ${className}`} aria-hidden="true">
      <div className="cube">
        <div>
          <span>
            <b>🔒</b>
            <span>Temporary processing</span>
          </span>
        </div>
        <div>
          <span>
            <b>🗑</b>
            <span>Delete session</span>
          </span>
        </div>
        <div>
          <span>
            <b>🚫</b>
            <span>No storage</span>
          </span>
        </div>
        <div>
          <span>
            <b>📖</b>
            <span>Information only</span>
          </span>
        </div>
      </div>
    </div>
  );
};
export default PrivacyCube;
