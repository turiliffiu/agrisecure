import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { nodesAPI } from '../api/services'
import {
  Radio,
  Wifi,
  WifiOff,
  Battery,
  BatteryLow,
  BatteryWarning,
  Signal,
  Thermometer,
  Shield,
  Router,
  Search,
  Filter
} from 'lucide-react'

const nodeTypeIcons = {
  gateway: Router,
  ambient: Thermometer,
  security: Shield,
}

const nodeTypeLabels = {
  gateway: 'Gateway',
  ambient: 'Ambientale',
  security: 'Sicurezza',
}

const statusColors = {
  online: 'bg-green-500',
  offline: 'bg-red-500',
  warning: 'bg-yellow-500',
}

function BatteryIcon({ level }) {
  if (level === null || level === undefined) return <Battery className="h-4 w-4 text-gray-400" />
  if (level < 20) return <BatteryLow className="h-4 w-4 text-red-500" />
  if (level < 50) return <BatteryWarning className="h-4 w-4 text-yellow-500" />
  return <Battery className="h-4 w-4 text-green-500" />
}

function SignalStrength({ rssi }) {
  if (rssi === null || rssi === undefined) return <Signal className="h-4 w-4 text-gray-400" />
  // RSSI: -30 = ottimo, -90 = scarso
  const strength = Math.min(100, Math.max(0, ((rssi + 90) / 60) * 100))
  const color = strength > 60 ? 'text-green-500' : strength > 30 ? 'text-yellow-500' : 'text-red-500'
  return <Signal className={`h-4 w-4 ${color}`} />
}

function NodeCard({ node }) {
  const TypeIcon = nodeTypeIcons[node.node_type] || Radio
  const lastSeen = node.last_seen ? new Date(node.last_seen) : null
  const lastSeenText = lastSeen 
    ? `${lastSeen.toLocaleDateString('it-IT')} ${lastSeen.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}`
    : 'Mai visto'

  return (
    <Link
      to={`/nodes/${node.id}`}
      className="block bg-white rounded-xl shadow-sm p-6 card-hover"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg ${node.status === 'online' ? 'bg-agri-100' : 'bg-gray-100'}`}>
            <TypeIcon className={`h-6 w-6 ${node.status === 'online' ? 'text-agri-600' : 'text-gray-400'}`} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{node.name || node.node_id}</h3>
            <p className="text-sm text-gray-500">{nodeTypeLabels[node.node_type] || node.node_type}</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <span className={`w-2.5 h-2.5 rounded-full ${statusColors[node.status] || 'bg-gray-400'}`}></span>
          <span className="text-sm text-gray-600 capitalize">{node.status}</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm">
        <div className="flex items-center space-x-2">
          <BatteryIcon level={node.battery_level} />
          <span className="text-gray-600">
            {node.battery_level !== null ? `${node.battery_level}%` : '-'}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <SignalStrength rssi={node.rssi} />
          <span className="text-gray-600">
            {node.rssi !== null ? `${node.rssi} dBm` : '-'}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          {node.status === 'online' ? (
            <Wifi className="h-4 w-4 text-green-500" />
          ) : (
            <WifiOff className="h-4 w-4 text-red-500" />
          )}
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100">
        <p className="text-xs text-gray-500">
          Ultimo contatto: {lastSeenText}
        </p>
      </div>

      {node.is_armed && (
        <div className="mt-3 flex items-center text-sm text-agri-600">
          <Shield className="h-4 w-4 mr-1" />
          Armato
        </div>
      )}
    </Link>
  )
}

export default function Nodes() {
  const [nodes, setNodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')

  useEffect(() => {
    fetchNodes()
  }, [])

  const fetchNodes = async () => {
    try {
      const response = await nodesAPI.getAll()
      setNodes(response.data.results || response.data)
    } catch (error) {
      console.error('Errore caricamento nodi:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredNodes = nodes.filter(node => {
    const matchesSearch = !search || 
      node.name?.toLowerCase().includes(search.toLowerCase()) ||
      node.node_id?.toLowerCase().includes(search.toLowerCase())
    const matchesType = filterType === 'all' || node.node_type === filterType
    const matchesStatus = filterStatus === 'all' || node.status === filterStatus
    return matchesSearch && matchesType && matchesStatus
  })

  const stats = {
    total: nodes.length,
    online: nodes.filter(n => n.status === 'online').length,
    offline: nodes.filter(n => n.status === 'offline').length,
    warning: nodes.filter(n => n.status === 'warning').length,
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-agri-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Nodi IoT</h1>
        <p className="text-gray-500">Gestisci e monitora i nodi del sistema</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-500">Totale</p>
          <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
        </div>
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-500">Online</p>
          <p className="text-2xl font-bold text-green-600">{stats.online}</p>
        </div>
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-500">Offline</p>
          <p className="text-2xl font-bold text-red-600">{stats.offline}</p>
        </div>
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-500">Warning</p>
          <p className="text-2xl font-bold text-yellow-600">{stats.warning}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Cerca nodo..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-agri-500 focus:border-agri-500"
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-agri-500 focus:border-agri-500"
          >
            <option value="all">Tutti i tipi</option>
            <option value="gateway">Gateway</option>
            <option value="ambient">Ambientale</option>
            <option value="security">Sicurezza</option>
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-agri-500 focus:border-agri-500"
          >
            <option value="all">Tutti gli stati</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
            <option value="warning">Warning</option>
          </select>
        </div>
      </div>

      {/* Nodes Grid */}
      {filteredNodes.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredNodes.map((node) => (
            <NodeCard key={node.id} node={node} />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <Radio className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">Nessun nodo trovato</p>
        </div>
      )}
    </div>
  )
}
