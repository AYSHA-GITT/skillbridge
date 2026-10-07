import React from 'react';
import { Navigate } from 'react-router-dom';

/**
 * Legacy FedViz route moved into the Institutional Admin Portal under:
 * Admin -> Federated Learning Center
 */
export default function FedViz() {
  return <Navigate to="/admin?tab=federated" replace />;
}
