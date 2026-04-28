import { useSearchParams } from 'react-router-dom'
import { Users, DollarSign, MapPin, Clock4 } from 'lucide-react'
import TradesPage from '@/pages/Trades'
import OverheadPage from '@/pages/Overhead'

type TabKey = 'trades' | 'overhead' | 'regional' | 'labor-rates'

const TABS: { key: TabKey; label: string; icon: any }[] = [
  { key: 'trades', label: 'Trades', icon: Users },
  { key: 'overhead', label: 'Overhead', icon: DollarSign },
  { key: 'regional', label: 'Regional Rates', icon: MapPin },
  { key: 'labor-rates', label: 'Labor Rates', icon: Clock4 },
]

function ComingSoon({ what }: { what: string }) {
  return (
    <div className="card p-12 text-center">
      <p className="text-gray-500 text-sm">
        <span className="font-medium text-gray-700">{what}</span> editor is coming with the next platform update.
      </p>
      <p className="text-xs text-gray-400 mt-2">
        Until then, defaults seeded by the backend are used automatically when you calculate a bid.
      </p>
    </div>
  )
}

export default function SettingsPage() {
  const [params, setParams] = useSearchParams()
  const raw = params.get('tab') as TabKey | null
  const active: TabKey = raw && TABS.some((t) => t.key === raw) ? raw : 'trades'

  const setTab = (next: TabKey) => {
    const newParams = new URLSearchParams(params)
    if (next === 'trades') newParams.delete('tab')
    else newParams.set('tab', next)
    setParams(newParams, { replace: true })
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium transition-colors -mb-px border-b-2 ${
              active === key
                ? 'text-blue-700 border-blue-700'
                : 'text-gray-500 border-transparent hover:text-gray-700'
            }`}
          >
            <Icon size={14} className="inline -mt-0.5 mr-1.5" />
            {label}
          </button>
        ))}
      </div>

      {active === 'trades' && <TradesPage />}
      {active === 'overhead' && <OverheadPage />}
      {active === 'regional' && <ComingSoon what="Regional cost multipliers" />}
      {active === 'labor-rates' && <ComingSoon what="Labor rates by region & trade category" />}
    </div>
  )
}
