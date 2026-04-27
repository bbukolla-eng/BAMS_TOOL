import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import Layout from '@/components/layout/Layout'
import LoginPage from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import ProjectsPage from '@/pages/Projects'
import ProjectDetail from '@/pages/ProjectDetail'
import DrawingsPage from '@/pages/Drawings'
import DrawingViewer from '@/pages/DrawingViewer'
import DrawingsAIPage from '@/pages/DrawingsAI'
import SpecsPage from '@/pages/Specs'
import TakeoffPage from '@/pages/Takeoff'
import PriceBookPage from '@/pages/PriceBook'
import TradesPage from '@/pages/Trades'
import OverheadPage from '@/pages/Overhead'
import BiddingPage from '@/pages/Bidding'
import BidSummaryPage from '@/pages/BidSummary'
import ProposalPage from '@/pages/Proposal'
import SubmittalsPage from '@/pages/Submittals'
import CloseoutPage from '@/pages/Closeout'
import EquipmentPage from '@/pages/Equipment'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:id" element={<ProjectDetail />} />
        <Route path="projects/:id/drawings" element={<DrawingsPage />} />
        <Route path="projects/:id/drawings/:drawingId" element={<DrawingViewer />} />
        <Route path="projects/:id/drawings-ai" element={<Navigate to="../drawings?tab=ai" replace />} />
        <Route path="projects/:id/specs" element={<SpecsPage />} />
        <Route path="projects/:id/takeoff" element={<TakeoffPage />} />
        <Route path="projects/:id/bidding" element={<BiddingPage />} />
        <Route path="projects/:id/bid-summary" element={<BidSummaryPage />} />
        <Route path="projects/:id/proposal" element={<ProposalPage />} />
        <Route path="projects/:id/submittals" element={<SubmittalsPage />} />
        <Route path="projects/:id/closeout" element={<CloseoutPage />} />
        <Route path="projects/:id/equipment" element={<EquipmentPage />} />
        <Route path="price-book" element={<PriceBookPage />} />
        <Route path="trades" element={<TradesPage />} />
        <Route path="overhead" element={<OverheadPage />} />
      </Route>
    </Routes>
  )
}
