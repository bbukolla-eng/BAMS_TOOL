import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '@/api/client'
import { FileImage, FileText, Calculator, Gavel, Package, ClipboardCheck, Wrench, Brain, BarChart3, FileSignature } from 'lucide-react'

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>()

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => api.get(`/projects/${id}`).then((r) => r.data),
  })

  if (!project) return <div className="p-6 text-gray-500">Loading...</div>

  const modules = [
    { label: 'Drawings', icon: FileImage, to: 'drawings', color: 'blue', desc: 'Upload & view MEP drawings' },
    { label: 'Drawings AI', icon: Brain, to: 'drawings-ai', color: 'purple', desc: 'AI analysis & symbol detection' },
    { label: 'Specs', icon: FileText, to: 'specs', color: 'teal', desc: 'Specification documents' },
    { label: 'Takeoff', icon: Calculator, to: 'takeoff', color: 'orange', desc: 'Quantity takeoff' },
    { label: 'Equipment', icon: Wrench, to: 'equipment', color: 'gray', desc: 'Equipment schedule' },
    { label: 'Bidding', icon: Gavel, to: 'bidding', color: 'yellow', desc: 'Bid generation' },
    { label: 'Bid Summary', icon: BarChart3, to: 'bid-summary', color: 'green', desc: 'Summary by trade & system' },
    { label: 'Proposal', icon: FileSignature, to: 'proposal', color: 'indigo', desc: 'Generate proposals' },
    { label: 'Submittals', icon: Package, to: 'submittals', color: 'pink', desc: 'Submittal log' },
    { label: 'Closeout', icon: ClipboardCheck, to: 'closeout', color: 'red', desc: 'O&M, warranties, as-builts' },
  ]

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
          <Link to="/projects" className="hover:text-blue-600">Projects</Link>
          <span>/</span>
          <span className="text-gray-900">{project.name}</span>
        </div>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
            <p className="text-sm text-gray-500 mt-1">
              {project.project_number && `#${project.project_number} · `}
              {[project.city, project.state].filter(Boolean).join(', ')}
              {project.bid_due_date && ` · Due ${new Date(project.bid_due_date).toLocaleDateString()}`}
            </p>
          </div>
          <span className={`text-sm font-medium px-3 py-1 rounded-full ${
            project.status === 'active' ? 'bg-green-100 text-green-700' :
            project.status === 'bidding' ? 'bg-yellow-100 text-yellow-700' :
            'bg-blue-100 text-blue-700'
          }`}>{project.status}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {modules.map(({ label, icon: Icon, to, color, desc }) => (
          <Link key={to} to={to} className="card p-4 hover:shadow-md transition-all hover:-translate-y-0.5">
            <div className={`w-9 h-9 rounded-lg bg-${color}-100 flex items-center justify-center mb-3`}>
              <Icon size={18} className={`text-${color}-600`} />
            </div>
            <p className="font-semibold text-sm text-gray-900">{label}</p>
            <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
