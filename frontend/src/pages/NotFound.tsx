import React from 'react';
import { Link } from 'react-router-dom';

const NotFound: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          <div className="mx-auto h-24 w-24 text-6xl mb-4">🕷️</div>
          <h2 className="text-3xl font-extrabold text-gray-900">404 - Page Not Found</h2>
          <p className="mt-2 text-sm text-gray-600">
            The page you're looking for doesn't exist.
          </p>
          <div className="mt-6">
            <Link
              to="/dashboard"
              className="btn-primary"
            >
              Go to Dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
