import { useState, useEffect } from 'react'
import { securityAPI } from '../api/services'
import {
  Bell,
  AlertTriangle,
  CheckCircle,
  Clock,
  User,
  Filter,
  RefreshCw,
  Eye,
  X
} from 'lucide-react'

const priorityConfig = {
  critical: { color: 'red', label: 'Critico', bg: 'bg-red-100 text-red-800' },
  high: { color: 'orange', label: 'Alto', bg: 'bg-orange-100 text-orange-800' },
  medium: { color: 'yellow', label: 'Medio', bg: 'bg-yellow-100 text-yellow-800' },
  low: { color: 'blue', label: 'Basso', bg: 'bg-blue-100 text-blue-800' },
}

const statusConfig = {
  active: { label: 'Attivo', bg: 'bg-red-100 text-red-800' },
  acknowledged: { label: 'Preso in carico', bg: 'bg-yellow-100 text-yellow-800' },
  resolved: { label: 'Risolto', bg: 'bg-green-100 text-green-800' },
}

const classificationLabels = {
  person: '🧑 Persona rilevata',
  tamper: '⚠️ Manomissione',
  animal_lg: '🦊 Animale grande',
  animal_sm: '🐈 Animale piccolo',
  unknown: '❓ Movimento sconosciuto',
}

function AlarmDetailModal({ alarm, onClose, onAction }) {
  const [notes, setNotes] = useState('')
  const [actionLoading, setActionLoading] = useState(null)

  const handleAction = async (action) => {
    setActionLoading(action)
    await onAction(alarm.id, action, notes)
    setActionLoading(null)
    if (action === 'resolve' || action === 'false_positive') {
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Dettagli Allarme</h3>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Classificazione:</span>
              <span className="font-medium">{classificationLabels[alarm.classification]}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Priorità:</span>
              <span className={`px-2 py-1 rounded text-sm ${priorityConfig[alarm.priority]?.bg}`}>
                {priorityConfig[alarm.priority]?.label}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Stato:</span>
              <span className={`px-2 py-1 rounded text-sm ${statusConfig[alarm.status]?.bg}`}>
                {statusConfig[alarm.status]?.label}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Nodo:</span>
              <span className="font-medium">{alarm.node_name || alarm.node}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Data/Ora:</span>
              <span>{new Date(alarm.triggered_at).toLocaleString('it-IT')}</span>
            </div>
            {alarm.acknowledged_at && (
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Preso in carico:</span>
                <span>{new Date(alarm.acknowledged_at).toLocaleString('it-IT')}</span>
              </div>
            )}
            {alarm.acknowledged_by && (
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Da:</span>
                <span>{alarm.acknowledged_by}</span>
              </div>
            )}

            {alarm.status !== 'resolved' && (
              <>
                <div className="border-t pt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Note (opzionale)
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-agri-500"
                    placeholder="Aggiungi note..."
                  />
                </div>

                <div className="flex flex-wrap gap-2 pt-4">
                  {alarm.status === 'active' && (
                    <button
                      onClick={() => handleAction('acknowledge')}
                      disabled={actionLoading}
                      className="flex-1 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50"
                    >
                      {actionLoading === 'acknowledge' ? 'Caricamento...' : 'Prendi in carico'}
                    </button>
                  )}
                  <button
                    onClick={() => handleAction('resolve')}
                    disabled={actionLoading}
                    className="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
                  >
                    {actionLoading === 'resolve' ? 'Caricamento...' : 'Risolvi'}
                  </button>
                  <button
                    onClick={() => handleAction('false_positive')}
                    disabled={actionLoading}
                    className="flex-1 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50"
                  >
                    {actionLoading === 'false_positive' ? 'Caricamento...' : 'Falso positivo'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function AlarmRow({ alarm, onClick }) {
  return (
    <tr 
      className="hover:bg-gray-50 cursor-pointer"
      onClick={() => onClick(alarm)}
    >
      <td className="px-6 py-4 whitespace-nowrap">
        <span className={`px-2 py-1 rounded text-xs font-medium ${priorityConfig[alarm.priority]?.bg}`}>
          {priorityConfig[alarm.priority]?.label}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className="text-gray-900">{classificationLabels[alarm.classification]}</span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-gray-500">
        {alarm.node_name || alarm.node}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-gray-500">
        {new Date(alarm.triggered_at).toLocaleString('it-IT')}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className={`px-2 py-1 rounded text-xs font-medium ${statusConfig[alarm.status]?.bg}`}>
          {statusConfig[alarm.status]?.label}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <button className="text-agri-600 hover:text-agri-700">
          <Eye className="h-5 w-5" />
        </button>
      </td>
    </tr>
  )
}

export default function Alarms() {
  const [alarms, setAlarms] = useState([])
  const [statistics, setStatistics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedAlarm, setSelectedAlarm] = useState(null)
  const [filterStatus, setFilterStatus] = useState('all')
  const [filterPriority, setFilterPriority] = useState('all')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [alarmsRes, statsRes] = await Promise.all([
        securityAPI.getAlarms(),
        securityAPI.getStatistics(30)
      ])
      setAlarms(alarmsRes.data.results || alarmsRes.data)
      setStatistics(statsRes.data)
    } catch (error) {
      console.error('Errore caricamento allarmi:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAlarmAction = async (alarmId, action, notes) => {
    try {
      await securityAPI.alarmAction(alarmId, action, notes)
      fetchData()
    } catch (error) {
      console.error('Errore azione allarme:', error)
      alert('Errore: ' + error.message)
    }
  }

  const filteredAlarms = alarms.filter(alarm => {
    if (filterStatus !== 'all' && alarm.status !== filterStatus) return false
    if (filterPriority !== 'all' && alarm.priority !== filterPriority) return false
    return true
  })

  const activeCount = alarms.filter(a => a.status === 'active').length
  const acknowledgedCount = alarms.filter(a => a.status === 'acknowledged').length

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Allarmi</h1>
          <p className="text-gray-500">Gestione allarmi di sicurezza</p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Aggiorna
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <AlertTriangle className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Attivi</p>
              <p className="text-2xl font-bold text-red-600">{activeCount}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <Clock className="h-5 w-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">In gestione</p>
              <p className="text-2xl font-bold text-yellow-600">{acknowledgedCount}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Risolti (30gg)</p>
              <p className="text-2xl font-bold text-green-600">{statistics?.by_status?.resolved || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gray-100 rounded-lg">
              <User className="h-5 w-5 text-gray-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Falsi positivi</p>
              <p className="text-2xl font-bold text-gray-600">
                {statistics?.false_positive_rate ? `${(statistics.false_positive_rate * 100).toFixed(0)}%` : '0%'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4 flex flex-wrap gap-4">
        <div className="flex items-center space-x-2">
          <Filter className="h-5 w-5 text-gray-400" />
          <span className="text-sm text-gray-600">Filtri:</span>
        </div>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-agri-500"
        >
          <option value="all">Tutti gli stati</option>
          <option value="active">Attivi</option>
          <option value="acknowledged">In gestione</option>
          <option value="resolved">Risolti</option>
        </select>
        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-agri-500"
        >
          <option value="all">Tutte le priorità</option>
          <option value="critical">Critico</option>
          <option value="high">Alto</option>
          <option value="medium">Medio</option>
          <option value="low">Basso</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {filteredAlarms.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Priorità
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tipo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Nodo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Data/Ora
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Stato
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Azioni
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredAlarms.map(alarm => (
                  <AlarmRow
                    key={alarm.id}
                    alarm={alarm}
                    onClick={setSelectedAlarm}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <Bell className="h-12 w-12 text-gray-300 mb-4" />
            <p>Nessun allarme trovato</p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedAlarm && (
        <AlarmDetailModal
          alarm={selectedAlarm}
          onClose={() => setSelectedAlarm(null)}
          onAction={handleAlarmAction}
        />
      )}
    </div>
  )
}
