import { useState, useEffect } from 'react'
import { securityAPI, nodesAPI } from '../api/services'
import {
  Shield,
  ShieldOff,
  ShieldCheck,
  Lock,
  Unlock,
  AlertTriangle,
  CheckCircle,
  Radio
} from 'lucide-react'

const armModes = [
  { id: 'away', label: 'Fuori Casa', description: 'Tutti i sensori attivi', icon: Lock },
  { id: 'home', label: 'In Casa', description: 'Solo perimetro esterno', icon: Shield },
  { id: 'night', label: 'Notte', description: 'Perimetro + zone interne selezionate', icon: ShieldCheck },
]

function ArmModeCard({ mode, selected, onClick, disabled }) {
  const Icon = mode.icon
  return (
    <button
      onClick={() => onClick(mode.id)}
      disabled={disabled}
      className={`p-6 rounded-xl border-2 text-left transition-all ${
        selected 
          ? 'border-agri-500 bg-agri-50' 
          : 'border-gray-200 hover:border-gray-300 bg-white'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <div className="flex items-center space-x-4">
        <div className={`p-3 rounded-lg ${selected ? 'bg-agri-100' : 'bg-gray-100'}`}>
          <Icon className={`h-6 w-6 ${selected ? 'text-agri-600' : 'text-gray-500'}`} />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900">{mode.label}</h3>
          <p className="text-sm text-gray-500">{mode.description}</p>
        </div>
      </div>
    </button>
  )
}

function NodeSelector({ nodes, selectedNodes, onChange }) {
  const handleToggle = (nodeId) => {
    if (selectedNodes.includes(nodeId)) {
      onChange(selectedNodes.filter(id => id !== nodeId))
    } else {
      onChange([...selectedNodes, nodeId])
    }
  }

  const handleSelectAll = () => {
    if (selectedNodes.length === nodes.length) {
      onChange([])
    } else {
      onChange(nodes.map(n => n.node_id))
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">Seleziona nodi da armare:</span>
        <button
          onClick={handleSelectAll}
          className="text-sm text-agri-600 hover:text-agri-700"
        >
          {selectedNodes.length === nodes.length ? 'Deseleziona tutti' : 'Seleziona tutti'}
        </button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {nodes.map(node => (
          <label
            key={node.id}
            className={`flex items-center p-3 rounded-lg border cursor-pointer transition-colors ${
              selectedNodes.includes(node.node_id)
                ? 'border-agri-500 bg-agri-50'
                : 'border-gray-200 hover:bg-gray-50'
            }`}
          >
            <input
              type="checkbox"
              checked={selectedNodes.includes(node.node_id)}
              onChange={() => handleToggle(node.node_id)}
              className="sr-only"
            />
            <div className={`w-4 h-4 rounded border mr-3 flex items-center justify-center ${
              selectedNodes.includes(node.node_id)
                ? 'bg-agri-500 border-agri-500'
                : 'border-gray-300'
            }`}>
              {selectedNodes.includes(node.node_id) && (
                <CheckCircle className="h-3 w-3 text-white" />
              )}
            </div>
            <div className="flex-1">
              <span className="font-medium text-gray-900">{node.name || node.node_id}</span>
              <span className={`ml-2 text-xs ${node.status === 'online' ? 'text-green-600' : 'text-red-600'}`}>
                ({node.status})
              </span>
            </div>
          </label>
        ))}
      </div>
    </div>
  )
}

export default function ArmSystem() {
  const [currentState, setCurrentState] = useState(null)
  const [nodes, setNodes] = useState([])
  const [selectedMode, setSelectedMode] = useState('away')
  const [selectedNodes, setSelectedNodes] = useState([])
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [armRes, nodesRes] = await Promise.all([
        securityAPI.getArmState(),
        nodesAPI.getAll()
      ])
      
      const armData = armRes.data.results?.[0] || armRes.data[0] || armRes.data
      setCurrentState(armData)
      
      const securityNodes = (nodesRes.data.results || nodesRes.data)
        .filter(n => n.node_type === 'security')
      setNodes(securityNodes)
      
      // Pre-seleziona tutti i nodi
      setSelectedNodes(securityNodes.map(n => n.node_id))
    } catch (error) {
      console.error('Errore caricamento stato:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleArm = async () => {
    if (selectedNodes.length === 0) {
      alert('Seleziona almeno un nodo')
      return
    }
    
    setActionLoading(true)
    try {
      await securityAPI.setArmState(selectedMode, selectedNodes, notes)
      await fetchData()
      setNotes('')
      alert('Sistema armato con successo!')
    } catch (error) {
      console.error('Errore armamento:', error)
      alert('Errore: ' + error.message)
    } finally {
      setActionLoading(false)
    }
  }

  const handleDisarm = async () => {
    setActionLoading(true)
    try {
      await securityAPI.setArmState('disarmed', [], notes)
      await fetchData()
      setNotes('')
      alert('Sistema disarmato!')
    } catch (error) {
      console.error('Errore disarmo:', error)
      alert('Errore: ' + error.message)
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-agri-600"></div>
      </div>
    )
  }

  const isArmed = currentState?.mode && currentState.mode !== 'disarmed'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Armamento Sistema</h1>
        <p className="text-gray-500">Gestisci lo stato di sicurezza del sistema</p>
      </div>

      {/* Current Status */}
      <div className={`rounded-xl p-6 ${isArmed ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'}`}>
        <div className="flex items-center space-x-4">
          <div className={`p-4 rounded-full ${isArmed ? 'bg-green-100' : 'bg-yellow-100'}`}>
            {isArmed ? (
              <Shield className="h-8 w-8 text-green-600" />
            ) : (
              <ShieldOff className="h-8 w-8 text-yellow-600" />
            )}
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              {isArmed ? 'Sistema ARMATO' : 'Sistema DISARMATO'}
            </h2>
            {isArmed && currentState?.mode && (
              <p className="text-gray-600">
                Modalità: {armModes.find(m => m.id === currentState.mode)?.label || currentState.mode}
              </p>
            )}
            {currentState?.changed_at && (
              <p className="text-sm text-gray-500">
                Ultimo cambio: {new Date(currentState.changed_at).toLocaleString('it-IT')}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Quick Disarm */}
      {isArmed && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">Disarma Sistema</h3>
              <p className="text-sm text-gray-500">Disattiva tutti i sensori di sicurezza</p>
            </div>
            <button
              onClick={handleDisarm}
              disabled={actionLoading}
              className="px-6 py-3 bg-red-500 text-white font-medium rounded-lg hover:bg-red-600 disabled:opacity-50 flex items-center"
            >
              <Unlock className="h-5 w-5 mr-2" />
              {actionLoading ? 'Disarmando...' : 'DISARMA'}
            </button>
          </div>
        </div>
      )}

      {/* Arm Controls */}
      {!isArmed && (
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-6">
          <h3 className="font-semibold text-gray-900">Arma Sistema</h3>
          
          {/* Mode Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Seleziona modalità:
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {armModes.map(mode => (
                <ArmModeCard
                  key={mode.id}
                  mode={mode}
                  selected={selectedMode === mode.id}
                  onClick={setSelectedMode}
                  disabled={actionLoading}
                />
              ))}
            </div>
          </div>

          {/* Node Selection */}
          {nodes.length > 0 && (
            <NodeSelector
              nodes={nodes}
              selectedNodes={selectedNodes}
              onChange={setSelectedNodes}
            />
          )}

          {nodes.length === 0 && (
            <div className="flex items-center p-4 bg-yellow-50 rounded-lg text-yellow-700">
              <AlertTriangle className="h-5 w-5 mr-2" />
              Nessun nodo di sicurezza configurato
            </div>
          )}

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Note (opzionale):
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-agri-500"
              placeholder="Es: Armato per la notte"
            />
          </div>

          {/* Arm Button */}
          <button
            onClick={handleArm}
            disabled={actionLoading || selectedNodes.length === 0}
            className="w-full py-4 bg-agri-600 text-white font-semibold rounded-lg hover:bg-agri-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            <Lock className="h-5 w-5 mr-2" />
            {actionLoading ? 'Armando il sistema...' : 'ARMA SISTEMA'}
          </button>
        </div>
      )}

      {/* Armed Nodes List */}
      {isArmed && currentState?.armed_nodes?.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Nodi Armati</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {nodes
              .filter(n => currentState.armed_nodes.includes(n.node_id))
              .map(node => (
                <div 
                  key={node.id}
                  className="flex items-center p-3 bg-green-50 rounded-lg"
                >
                  <Radio className="h-4 w-4 text-green-600 mr-2" />
                  <span className="text-green-800">{node.name || node.node_id}</span>
                </div>
              ))
            }
          </div>
        </div>
      )}
    </div>
  )
}
