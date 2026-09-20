import React from 'react';
import { AssuranceProvider, useAssurance } from './context/AssuranceContext';
import { Topbar } from './components/layout/Topbar';
import { Sidebar } from './components/layout/Sidebar';
import { FindingDetailModal } from './components/evidence/FindingDetailModal';
import { ContributorDetailDrawer } from './components/evidence/ContributorDetailDrawer';

// Pages
import { AssuranceOverview } from './pages/AssuranceOverview';
import { DataIntegrityPage } from './pages/DataIntegrityPage';
import { ModelIntegrityPage } from './pages/ModelIntegrityPage';
import { InferenceIntegrityPage } from './pages/InferenceIntegrityPage';
import { DistributionShiftPage } from './pages/DistributionShiftPage';
import { ContributorRiskPage } from './pages/ContributorRiskPage';
import { AuditTrailPage } from './pages/AuditTrailPage';
import { FindingsEvidencePage } from './pages/FindingsEvidencePage';
import { ReportsPage } from './pages/ReportsPage';
import { SystemCoveragePage } from './pages/SystemCoveragePage';

const AppContent: React.FC = () => {
  const { 
    activeTab, 
    selectedFinding, 
    setSelectedFinding, 
    selectedContributor, 
    setSelectedContributor 
  } = useAssurance();

  const renderActivePage = () => {
    switch (activeTab) {
      case 'overview':
        return <AssuranceOverview />;
      case 'data':
        return <DataIntegrityPage />;
      case 'model':
        return <ModelIntegrityPage />;
      case 'inference':
        return <InferenceIntegrityPage />;
      case 'shift':
        return <DistributionShiftPage />;
      case 'contributors':
        return <ContributorRiskPage />;
      case 'audit':
        return <AuditTrailPage />;
      case 'findings':
        return <FindingsEvidencePage />;
      case 'reports':
        return <ReportsPage />;
      case 'coverage':
        return <SystemCoveragePage />;
      default:
        return <AssuranceOverview />;
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      <Topbar />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 relative">
          <div className="max-w-7xl mx-auto">
            {renderActivePage()}
          </div>
        </main>
      </div>

      {/* Global Modals & Drawers */}
      <FindingDetailModal
        finding={selectedFinding}
        onClose={() => setSelectedFinding(null)}
      />

      <ContributorDetailDrawer
        profile={selectedContributor}
        onClose={() => setSelectedContributor(null)}
      />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AssuranceProvider>
      <AppContent />
    </AssuranceProvider>
  );
};

export default App;
