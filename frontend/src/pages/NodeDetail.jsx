import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { nodesAPI, sensorsAPI } from '../api/services'
import {
  ArrowLeft,
  Radio,
  Wifi,
  WifiOff,
  Battery,
  Signal,
  Thermometer,
  Shield,
  Router,
  Clock,
  MapPin,
  RefreshCw,
  Send
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const nodeTypeIcons = {
  gateway: Router,
  ambient: Thermometer,
  security: Shield,
}

export default function NodeDetail() {
  const { id } = useParams()
  const [node, setNode] = useState(null)
  const [heartbeats, setHeartbeats] = useState([])
  const [sensorData, setSensorData] = useState([])
  const [loading, setLoading] = useState(true)
  const [command, setCommand] = useState('')
  const [sending, setSending] = useState(false)

  useEffect(() => {
    fetchNodeData()
  }, [id])

  const fetchNodeData = async () => {
    try {
      const [nodeRes, heartbeatsRes] = await Promise.all([
        nodesAPI.getById(id),
        nodesAPI.getHeartbeats(id, 24)
      ])
      
      setNode(nodeRes.data)
      setHeartbeats(heartbeatsRes.data.results || heartbeatsRes.data)

      // Se è un nodo ambientale, carica dati sensori
      if (nodeRes.data.node_type === 'ambient') {
        const sensorRes = await sensorsAPI.getChartData(nodeRes.data.node_id, 24)
        if (sensorRes.data) {
          const formatted = sensorRes.data.map(item => ({
            time: new Date(item.timestamp).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }),
            temperatura: item.temperature,
            umidità: item.humidity,
          }))
          setSensorData(formatted)
        }
      }
    } catch (error) {
      console.error('Errore caricamento nodo:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSendCommand = async () => {
    if (!command.trim()) return
    setSending(true)
    try {
      await nodesAPI.sendCommand(id, command, {})
      setCommand('')
      alert('Comando inviato!')
    } catch (error) {
      alert('Errore invio comando: ' + error.message)
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-agri-600"></div>
      </div>
    )
  }

  if (!node) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Nodo non trovato</p>
        <Link to="/nodes" className="text-agri-600 hover:underline mt-2 inline-block">
          Torna alla lista
        </Link>
      </div>
    )
  }

  const TypeIcon = nodeTypeIcons[node.node_type] || Radio
  const lastSeen = node.last_seen ? new Date(node.last_seen) : null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Link
          to="/nodes"
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <ArrowLeft className="h-5 w-5 text-gray-600" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{node.name || node.node_id}</h1>
          <p className="text-gray-500">ID: {node.node_id}</p>
        </div>
        <button
          onClick={fetchNodeData}
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <RefreshCw className="h-5 w-5 text-gray-600" />
        </button>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${node.status === 'online' ? 'bg-green-100' : 'bg-red-100'}`}>
              {node.status === 'online' ? (
                <Wifi className="h-5 w-5 text-green-600" />
              ) : (
                <WifiOff className="h-5 w-5 text-red-600" />
              )}
            </div>
            <div>
              <p className="text-sm text-gray-500">Stato</p>
              <p className="font-semibold text-gray-900 capitalize">{node.status}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-blue-100">
              <TypeIcon className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Tipo</p>
              <p className="font-semibold text-gray-900 capitalize">{node.node_type}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${node.battery_level < 20 ? 'bg-red-100' : 'bg-green-100'}`}>
              <Battery className={`h-5 w-5 ${node.battery_level < 20 ? 'text-red-600' : 'text-green-600'}`} />
            </div>
            <div>
              <p className="text-sm text-gray-500">Batteria</p>
              <p className="font-semibold text-gray-900">
                {node.battery_level !== null ? `${node.battery_level}%` : '-'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-purple-100">
              <Signal className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Segnale</p>
              <p className="font-semibold text-gray-900">
                {node.rssi !== null ? `${node.rssi} dBm` : '-'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Dettagli e Grafico */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Dettagli */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Dettagli</h3>
          <div className="space-y-4">
            <div className="flex items-center text-sm">
              <Clock className="h-4 w-4 text-gray-400 mr-2" />
              <span className="text-gray-500">Ultimo contatto:</span>
              <span className="ml-auto text-gray-900">
                {lastSeen ? lastSeen.toLocaleString('it-IT') : 'Mai'}
              </span>
            </div>
            <div className="flex items-center text-sm">
              <MapPin className="h-4 w-4 text-gray-400 mr-2" />
              <span className="text-gray-500">Posizione:</span>
              <span className="ml-auto text-gray-900">
                {node.latitude && node.longitude 
                  ? `${node.latitude.toFixed(4)}, ${node.longitude.toFixed(4)}`
                  : '-'
                }
              </span>
            </div>
            {node.firmware_version && (
              <div className="flex items-center text-sm">
                <span className="text-gray-500">Firmware:</span>
                <span className="ml-auto text-gray-900">{node.firmware_version}</span>
              </div>
            )}
            {node.uptime && (
              <div className="flex items-center text-sm">
                <span className="text-gray-500">Uptime:</span>
                <span className="ml-auto text-gray-900">
                  {Math.floor(node.uptime / 3600)}h {Math.floor((node.uptime % 3600) / 60)}m
                </span>
              </div>
            )}
            {node.is_armed !== undefined && (
              <div className="flex items-center text-sm">
                <Shield className="h-4 w-4 text-gray-400 mr-2" />
                <span className="text-gray-500">Armato:</span>
                <span className={`ml-auto font-medium ${node.is_armed ? 'text-green-600' : 'text-gray-600'}`}>
                  {node.is_armed ? 'Sì' : 'No'}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Grafico Sensori (solo per nodi ambientali) */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            {node.node_type === 'ambient' ? 'Dati Sensori (24h)' : 'Heartbeat (24h)'}
          </h3>
          {sensorData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={sensorData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Line type="monotone" dataKey="temperatura" stroke="#ef4444" name="Temp (°C)" dot={false} />
                <Line type="monotone" dataKey="umidità" stroke="#3b82f6" name="Umidità (%)" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-500">
              Nessun dato disponibile
            </div>
          )}
        </div>
      </div>

      {/* Invio Comandi */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Invia Comando</h3>
        <div className="flex space-x-4">
          <select
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-agri-500 focus:border-agri-500"
          >
            <option value="">Seleziona comando...</option>
            <option value="reboot">Riavvia</option>
            <option value="status">Richiedi stato</option>
            <option value="config_refresh">Aggiorna configurazione</option>
            {node.node_type === 'security' && (
              <>
                <option value="arm">Arma</option>
                <option value="disarm">Disarma</option>
                <option value="test_siren">Test sirena</option>
              </>
            )}
          </select>
          <button
            onClick={handleSendCommand}
            disabled={!command || sending}
            className="px-6 py-2 bg-agri-600 text-white rounded-lg hover:bg-agri-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            <Send className="h-4 w-4 mr-2" />
            {sending ? 'Invio...' : 'Invia'}
          </button>
        </div>
      </div>
    </div>
  )
}
